import random
import dataclasses # For PDCP_PDU copy
from .pdcp_packet import PDCP_PDU
import logging

logger = logging.getLogger(__name__)

class ImpairedChannel:
    def __init__(self, loss_rate: float, reordering_rate: float, 
                 duplication_rate: float, corruption_rate: float,
                 reorder_buffer_size: int = 10): # reorder_buffer_size for channel's internal mechanism
        self.loss_rate = loss_rate
        self.reordering_rate = reordering_rate
        self.duplication_rate = duplication_rate
        self.corruption_rate = corruption_rate
        
        # Internal buffer for simulating reordering by delaying packets
        self.channel_internal_buffer = [] 
        self.reorder_buffer_size = reorder_buffer_size # Max packets held by channel to induce reordering

        self.stats = {
            "total_passed_through": 0,
            "total_lost": 0,
            "total_duplicated": 0,
            "total_corrupted": 0,
            "total_reordered_events": 0 # Count how many times reordering logic was triggered
        }
        logger.info(f"ImpairedChannel initialized: Loss={loss_rate*100}%, Reorder={reordering_rate*100}%, Duplication={duplication_rate*100}%, Corruption={corruption_rate*100}%")

    def transmit(self, pdu_list: list[PDCP_PDU]) -> list[PDCP_PDU]:
        """
        Processes a list of PDUs, applying impairments.
        Reordering is simulated by potentially holding packets and releasing them out of order.
        """
        output_pdus_from_channel = []

        # Add incoming PDUs to the channel's internal buffer first
        for pdu_in in pdu_list:
            # 1. Loss
            if random.random() < self.loss_rate:
                logger.debug(f"CHANNEL: PDU SDU_ID={pdu_in.sdu_id} (SN={pdu_in.sn}) LOST.")
                self.stats["total_lost"] += 1
                continue  # PDU is lost

            # 2. Corruption
            pdu_processed = dataclasses.replace(pdu_in) # Work on a copy
            if random.random() < self.corruption_rate:
                pdu_processed.is_corrupted = True
                self.stats["total_corrupted"] += 1
                logger.debug(f"CHANNEL: PDU SDU_ID={pdu_processed.sdu_id} (SN={pdu_processed.sn}) CORRUPTED.")

            # 3. Duplication
            # Duplicates are added to the buffer along with the original (if not lost)
            self.channel_internal_buffer.append(pdu_processed)
            if random.random() < self.duplication_rate:
                duplicate_pdu = dataclasses.replace(pdu_processed) # Copy the (potentially corrupted) PDU
                # Note: A duplicated corrupted packet is still a corrupted packet.
                self.channel_internal_buffer.append(duplicate_pdu)
                self.stats["total_duplicated"] += 1
                logger.debug(f"CHANNEL: PDU SDU_ID={pdu_processed.sdu_id} (SN={pdu_processed.sn}) DUPLICATED.")
        
        # 4. Reordering logic based on channel_internal_buffer
        # This reordering model: if reordering event occurs, shuffle the current buffer.
        # More advanced: delay some packets, release others.
        if self.channel_internal_buffer and random.random() < self.reordering_rate:
            if len(self.channel_internal_buffer) > 1:
                random.shuffle(self.channel_internal_buffer)
                self.stats["total_reordered_events"] += 1
                logger.debug(f"CHANNEL: Reordering event triggered. Internal buffer (size {len(self.channel_internal_buffer)}) shuffled.")

        # Decide what to release from the channel_internal_buffer
        # Simple model: release all packets currently in buffer.
        # This means reordering only happens among packets that arrive "close" together.
        if self.channel_internal_buffer:
            output_pdus_from_channel.extend(self.channel_internal_buffer)
            self.stats["total_passed_through"] += len(self.channel_internal_buffer)
            self.channel_internal_buffer.clear()
            
        return output_pdus_from_channel

    def get_stats(self):
        return self.stats