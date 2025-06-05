import collections
import logging
from .pdcp_packet import PDCP_SDU, PDCP_PDU

# Setup basic logging
logger = logging.getLogger(__name__)

class PDCPTransmitter:
    def __init__(self, sn_length: int):
        if sn_length not in [12, 18]:
            raise ValueError("SN_LENGTH_BITS must be 12 or 18")
        self.sn_length = sn_length
        self.tx_next = 0  # 32-bit internal COUNT, initial value 0
        self.max_sn_value = (2**self.sn_length) - 1
        self.modulus = 2**self.sn_length
        self.hfn_bits = 32 - sn_length
        logger.info(f"PDCPTransmitter initialized with SN length: {sn_length} bits, Max SN: {self.max_sn_value}")

    def send_sdu(self, sdu_id: int, sdu_payload: str) -> PDCP_PDU:
        sdu = PDCP_SDU(id=sdu_id, payload=sdu_payload)
        
        sdu_count = self.tx_next
        pdcp_sn = sdu_count % self.modulus
        hfn = sdu_count >> self.sn_length
        
        pdu = PDCP_PDU(
            sdu_id=sdu.id,
            sn=pdcp_sn,
            count=sdu_count, # Full COUNT for reference/logging
            hfn=hfn,         # HFN for reference/logging
            original_sdu_payload=sdu.payload
        )
        
        logger.debug(f"TX: Sending SDU_ID={sdu.id}, Assigned COUNT={sdu_count}, SN={pdcp_sn}, HFN={hfn}")
        
        self.tx_next = (self.tx_next + 1) % (2**32) # Increment and wrap around 32-bit COUNT

        return pdu

class PDCPReceiver:
    def __init__(self, sn_length: int, t_reordering_threshold: int):
        if sn_length not in [12, 18]:
            raise ValueError("SN_LENGTH_BITS must be 12 or 18")
        self.sn_length = sn_length
        self.modulus = 2**self.sn_length
        self.max_sn_value = self.modulus - 1
        
        # Window_Size for HFN calculation (Clause 7.2 of 38.323, or 5.2.2.1)
        # "Window_Size = 2^(PDCP_SN_Size – 1)"
        self.window_size_hfn_calc = 2**(self.sn_length - 1)

        self.rx_deliv = 0  # COUNT of the first SDU not yet delivered to upper layers
        self.rx_next = 0   # Next expected COUNT from lower layers (highest received COUNT + 1)
        
        self.reordering_buffer = {}  # Key: COUNT, Value: PDCP_PDU
        self.received_counts_for_duplicate_check = set() # To quickly check for duplicates (already processed/buffered)

        # t-Reordering timer related attributes
        self.t_reordering_threshold = t_reordering_threshold # Max PDUs to wait if gap
        self.t_reordering_timer_active = False
        self.t_reordering_start_rx_reord = 0 # COUNT that was rx_deliv when timer started (RX_REORD in spec)
        self.pdus_processed_since_timer_start = 0

        # Stats
        self.delivered_sdu_ids = set()
        self.discarded_duplicates_count = 0
        self.discarded_old_count = 0
        self.discarded_corrupted_count = 0
        self.out_of_order_deliveries = 0 # Due to t-Reordering expiry

        logger.info(f"PDCPReceiver initialized with SN length: {sn_length} bits, HFN Calc Window: {self.window_size_hfn_calc}, t-Reordering Threshold: {t_reordering_threshold}")

    def _calculate_hfn_from_rcvd_sn(self, rcvd_sn: int) -> int:
        # Implements HFN estimation logic from Clause 5.2.2.1 of 3GPP TS 38.323
        # HFN part of RX_DELIV
        hfn_rx_deliv = self.rx_deliv >> self.sn_length
        # SN part of RX_DELIV
        sn_rx_deliv = self.rx_deliv % self.modulus

        # Ensure rcvd_sn is within valid range
        if not (0 <= rcvd_sn <= self.max_sn_value):
            logger.error(f"RX: Received invalid SN {rcvd_sn}. Max SN is {self.max_sn_value}. Discarding based on this.")
            # This case should ideally not happen if PDU SN is correctly formed
            # Or could be result of corruption not caught by is_corrupted flag
            return -1 # Indicate error

        derived_hfn = hfn_rx_deliv
        # Condition uses strict inequality for '<' and '>=' for Window_Size boundary
        if rcvd_sn < (sn_rx_deliv - self.window_size_hfn_calc):
            derived_hfn = hfn_rx_deliv + 1
        elif rcvd_sn >= (sn_rx_deliv + self.window_size_hfn_calc):
            derived_hfn = hfn_rx_deliv - 1
        
        # HFN must be positive, but intermediate derived_hfn can be -1 if hfn_rx_deliv is 0
        # The resulting COUNT calculation will handle this with 32-bit unsigned arithmetic.
        return derived_hfn

    def receive_pdu(self, pdu: PDCP_PDU):
        logger.debug(f"RX: Received PDU: SN={pdu.sn}, SDU_ID={pdu.sdu_id}, (TX COUNT={pdu.count})")

        if pdu.is_corrupted:
            self.discarded_corrupted_count += 1
            logger.warning(f"RX: Discarding corrupted PDU with SN={pdu.sn}, SDU_ID={pdu.sdu_id}")
            return

        derived_hfn = self._calculate_hfn_from_rcvd_sn(pdu.sn)
        if derived_hfn == -1: # Error from HFN calculation (e.g. invalid SN)
            logger.error(f"RX: HFN calculation failed for PDU SN={pdu.sn}. Discarding.")
            # This might be another category of discard.
            return

        # Reconstruct COUNT: (HFN << SN_len) | SN. Ensure it's 32-bit unsigned.
        rcvd_count = ((derived_hfn << self.sn_length) | pdu.sn) & 0xFFFFFFFF
        logger.debug(f"RX: PDU SN={pdu.sn}. RX_DELIV={self.rx_deliv} (SN={self.rx_deliv % self.modulus}, HFN={self.rx_deliv >> self.sn_length}). Derived HFN={derived_hfn}. Reconstructed COUNT={rcvd_count}.")

        # Duplicate Check (Clause 5.2.2.2.3 from 38.323)
        # "if the SDU corresponding to the received PDCP PDU has already been received"
        # We check based on rcvd_count. If this COUNT was already delivered or is in buffer.
        if rcvd_count in self.received_counts_for_duplicate_check:
            self.discarded_duplicates_count += 1
            logger.info(f"RX: Discarding duplicate PDU with reconstructed COUNT={rcvd_count} (SN={pdu.sn}, SDU_ID={pdu.sdu_id})")
            return

        # Old Packet Check (Clause 5.2.2.2.3)
        # "if the COUNT value of the received PDCP PDU < RX_DELIV"
        if rcvd_count < self.rx_deliv:
            self.discarded_old_count += 1
            logger.info(f"RX: Discarding old PDU: rcvd_count={rcvd_count} < RX_DELIV={self.rx_deliv} (SN={pdu.sn}, SDU_ID={pdu.sdu_id})")
            return
        
        # Optional: Check for too far ahead (outside reordering window, 38.323 Clause 5.2.2.2.3)
        # Reordering_Window is typically 2**SN_LENGTH.
        # if rcvd_count >= self.rx_deliv + self.modulus: # self.modulus acts as Reordering_Window here
        #     logger.warning(f"RX: Discarding PDU too far ahead: rcvd_count={rcvd_count}, RX_DELIV={self.rx_deliv}. (SN={pdu.sn})")
        #     self.discarded_old_count += 1 # Or a different counter
        #     return

        # Add to reordering buffer and mark as seen
        if rcvd_count not in self.reordering_buffer :
             self.reordering_buffer[rcvd_count] = pdu
             self.received_counts_for_duplicate_check.add(rcvd_count) # Add here to prevent re-adding if processing stalls
             logger.debug(f"RX: Buffered PDU with COUNT={rcvd_count}, SN={pdu.sn}. Buffer size: {len(self.reordering_buffer)}")
        else: # Should be caught by "received_counts_for_duplicate_check" earlier, but as a safeguard.
            self.discarded_duplicates_count += 1
            logger.info(f"RX: Discarding duplicate PDU (already in buffer) with COUNT={rcvd_count}")
            return


        # Update RX_NEXT (highest received PDU COUNT + 1)
        self.rx_next = max(self.rx_next, (rcvd_count + 1) % (2**32))

        # In-order delivery
        self._try_in_order_delivery()

        # t-Reordering timer logic
        self._manage_t_reordering_timer()
        
        # If timer is active, increment counter for PDUs processed
        if self.t_reordering_timer_active:
            self.pdus_processed_since_timer_start +=1


    def _try_in_order_delivery(self):
        # Deliver PDUs that are now in-sequence
        while self.rx_deliv in self.reordering_buffer:
            pdu_to_deliver = self.reordering_buffer.pop(self.rx_deliv)
            # "Deliver SDU to upper layers"
            self.delivered_sdu_ids.add(pdu_to_deliver.sdu_id)
            logger.info(f"RX: Delivered SDU_ID={pdu_to_deliver.sdu_id} (COUNT={self.rx_deliv}, SN={pdu_to_deliver.sn}) in-order.")
            
            # self.received_counts_for_duplicate_check.remove(self.rx_deliv) # No, keep it to detect future duplicates
            
            self.rx_deliv = (self.rx_deliv + 1) % (2**32)
            
            # If timer was active but gap is now filled
            if self.t_reordering_timer_active and self.rx_deliv == self.t_reordering_start_rx_reord:
                 # This check might be too simple, check based on buffer state
                 pass


        # If buffer is empty or rx_deliv has caught up (no more gaps before rx_next), stop timer
        is_gap_present = False
        if self.reordering_buffer:
            # Check if the current rx_deliv is the smallest key in buffer
            # and if there are other packets up to rx_next that are missing
            if self.rx_deliv < self.rx_next and self.rx_deliv not in self.reordering_buffer:
                 is_gap_present = True
        
        if not is_gap_present and self.t_reordering_timer_active:
            logger.debug(f"RX: No gap detected or buffer empty. Stopping t-Reordering timer. RX_DELIV={self.rx_deliv}")
            self.t_reordering_timer_active = False
            self.pdus_processed_since_timer_start = 0


    def _manage_t_reordering_timer(self):
        # Check if a gap exists: buffer is not empty, and rx_deliv is not in buffer but is less than rx_next
        gap_exists = False
        if self.reordering_buffer: # Buffer must not be empty
            # A gap exists if rx_deliv is not the next item in buffer AND rx_deliv < rx_next
            # More simply: if rx_deliv is not in buffer, but rx_deliv < min(reordering_buffer.keys())
            # Or, if rx_deliv is not in buffer and rx_deliv < rx_next (meaning we expect something)
            if self.rx_deliv not in self.reordering_buffer and self.rx_deliv < self.rx_next:
                gap_exists = True

        if gap_exists:
            if not self.t_reordering_timer_active:
                self.t_reordering_timer_active = True
                self.t_reordering_start_rx_reord = self.rx_deliv # RX_REORD in spec: COUNT of first SDU not delivered
                self.pdus_processed_since_timer_start = 0
                logger.info(f"RX: Gap detected. RX_DELIV={self.rx_deliv}, RX_NEXT={self.rx_next}. t-Reordering timer started. RX_REORD set to {self.t_reordering_start_rx_reord}.")
            elif self.pdus_processed_since_timer_start >= self.t_reordering_threshold:
                logger.warning(f"RX: t-Reordering timer expired! RX_DELIV={self.rx_deliv}, RX_REORD={self.t_reordering_start_rx_reord}, Threshold={self.t_reordering_threshold} met.")
                # Deliver buffered PDUs up to RX_NEXT, even if out of order relative to RX_DELIV
                # The spec (TS 38.323, 5.2.2.2.2 t-Reordering) says:
                # - update RX_DELIV to the COUNT value of the first PDCP SDU that has not been received;
                # - deliver the PDCP SDUs that have not been delivered to upper layers and discard the remaining PDCP SDUs.
                # This means delivering from t_reordering_start_rx_reord up to rx_next, if available.
                
                # Simplified: deliver whatever is in buffer up to rx_next in COUNT order.
                counts_to_deliver_on_expiry = sorted([
                    c for c in self.reordering_buffer.keys() if c < self.rx_next
                ])

                last_delivered_count = self.rx_deliv -1 # if rx_deliv is 0, this is -1
                if last_delivered_count < 0 and self.rx_deliv == 0 : last_delivered_count = -1 # to handle initial state correctly

                for count_val in counts_to_deliver_on_expiry:
                    pdu_to_deliver = self.reordering_buffer.pop(count_val)
                    self.delivered_sdu_ids.add(pdu_to_deliver.sdu_id)
                    # self.received_counts_for_duplicate_check.remove(count_val) # No, keep for future checks
                    
                    if count_val != (last_delivered_count + 1) % (2**32) and count_val >= self.rx_deliv : # Check if it's out of the current rx_deliv sequence
                        self.out_of_order_deliveries += 1
                        logger.warning(f"RX: Delivering SDU_ID={pdu_to_deliver.sdu_id} (COUNT={count_val}) OUT OF ORDER due to t-Reordering expiry.")
                    else:
                        logger.info(f"RX: Delivering SDU_ID={pdu_to_deliver.sdu_id} (COUNT={count_val}) due to t-Reordering expiry.")
                    last_delivered_count = count_val

                # Update RX_DELIV: "to the COUNT value of the first PDCP SDU that has not been received"
                # This generally means advancing RX_DELIV past the gap that triggered the timer, up to RX_NEXT.
                # Or find the new lowest COUNT not yet delivered.
                # If everything up to rx_next was delivered or not present, rx_deliv becomes rx_next
                
                # A robust way:
                # Start searching from the original RX_REORD value
                new_rx_deliv = self.t_reordering_start_rx_reord
                while new_rx_deliv < self.rx_next and new_rx_deliv not in self.reordering_buffer:
                    # If new_rx_deliv was delivered (check delivered_sdu_ids by mapping back to PDU if needed)
                    # or simply assume anything not in buffer up to rx_next is "handled" (lost or delivered)
                    new_rx_deliv = (new_rx_deliv + 1) % (2**32)
                
                # If buffer is now empty or remaining items are all >= rx_next
                if not self.reordering_buffer or min(self.reordering_buffer.keys()) >= self.rx_next:
                    self.rx_deliv = self.rx_next
                else: # There are still items in buffer < rx_next
                    self.rx_deliv = min(self.reordering_buffer.keys())


                logger.info(f"RX: After t-Reordering expiry processing, new RX_DELIV={self.rx_deliv}. Buffer size: {len(self.reordering_buffer)}")
                
                self.t_reordering_timer_active = False
                self.pdus_processed_since_timer_start = 0
                
                # Attempt in-order delivery again with new rx_deliv
                self._try_in_order_delivery()
        
        # If timer is active, but the condition that started it (gap) is no longer true
        # (e.g. rx_deliv caught up, or buffer became empty)
        # This is handled in _try_in_order_delivery's end.


    def get_status(self):
        return {
            "delivered_sdu_count": len(self.delivered_sdu_ids),
            "buffered_pdu_count": len(self.reordering_buffer),
            "discarded_duplicates": self.discarded_duplicates_count,
            "discarded_old": self.discarded_old_count,
            "discarded_corrupted": self.discarded_corrupted_count,
            "out_of_order_deliveries": self.out_of_order_deliveries,
            "rx_deliv": self.rx_deliv,
            "rx_next": self.rx_next,
            "reordering_buffer_keys": sorted(list(self.reordering_buffer.keys()))[:10] # First 10 keys for brevity
        }

    def flush_buffer(self):
        """Called at the end of simulation to process remaining buffered packets."""
        logger.info("RX: Flushing reordering buffer at end of simulation.")
        # Similar to t-Reordering expiry, but deliver everything in order
        counts_to_deliver = sorted(self.reordering_buffer.keys())
        for count_val in counts_to_deliver:
            if count_val == self.rx_deliv : # Deliver in order
                pdu_to_deliver = self.reordering_buffer.pop(count_val)
                self.delivered_sdu_ids.add(pdu_to_deliver.sdu_id)
                logger.info(f"RX: Delivered SDU_ID={pdu_to_deliver.sdu_id} (COUNT={self.rx_deliv}) during flush.")
                self.rx_deliv = (self.rx_deliv + 1) % (2**32)
            elif count_val > self.rx_deliv : # A gap still exists
                logger.warning(f"RX: SDU for COUNT={self.rx_deliv} missing. SDU for COUNT={count_val} (SDU_ID {self.reordering_buffer[count_val].sdu_id}) remains in buffer or is lost.")
                # For simplicity, we just deliver what's next in order.
                # If we want to deliver out of order, change logic here.
                # For now, this means only contiguous delivery from rx_deliv.
                break # Stop if there is a gap.
        
        remaining_in_buffer = len(self.reordering_buffer)
        if remaining_in_buffer > 0:
            logger.warning(f"RX: {remaining_in_buffer} PDUs remain in buffer after flush, likely due to preceding losses.")