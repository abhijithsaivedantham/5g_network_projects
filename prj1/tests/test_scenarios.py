import dataclasses
import unittest
import logging
from src.pdcp_entity import PDCPTransmitter, PDCPReceiver
from src.channel_simulator import ImpairedChannel
from src.pdcp_packet import PDCP_PDU
import config as sim_config # Default config

# Suppress INFO/DEBUG logs from src during tests for cleaner output, unless specifically debugging tests.
# logging.getLogger('src.pdcp_entity').setLevel(logging.WARNING)
# logging.getLogger('src.channel_simulator').setLevel(logging.WARNING)

class TestPDCPSimulationScenarios(unittest.TestCase):

    def setUp(self):
        self.sn_length = 12 # Default for most tests for faster wrap-around
        self.tx = PDCPTransmitter(sn_length=self.sn_length)
        self.rx = PDCPReceiver(sn_length=self.sn_length, t_reordering_threshold=sim_config.T_REORDERING_THRESHOLD)
        # Basic channel, impairments configured per test
        self.channel = ImpairedChannel(0, 0, 0, 0) 
        self.num_packets_default = 100 # Small number for basic tests

    def _run_loop(self, num_packets, tx_entity, channel_entity, rx_entity):
        sent_pdus_info = [] # Store (sdu_id, original_count)
        for i in range(num_packets):
            pdu = tx_entity.send_sdu(sdu_id=i, sdu_payload=f"data_{i}")
            sent_pdus_info.append({"sdu_id": i, "tx_count": pdu.count, "tx_sn": pdu.sn})
            
            pdus_from_channel = channel_entity.transmit([pdu])
            for p_out_ch in pdus_from_channel:
                rx_entity.receive_pdu(p_out_ch)
        rx_entity.flush_buffer() # Ensure all processable packets are delivered
        return sent_pdus_info

    def test_normal_flow_no_impairments(self):
        self.channel.loss_rate = 0
        self.channel.reordering_rate = 0
        self.channel.duplication_rate = 0
        self.channel.corruption_rate = 0
        
        self._run_loop(self.num_packets_default, self.tx, self.channel, self.rx)
        
        stats = self.rx.get_status()
        self.assertEqual(stats["delivered_sdu_count"], self.num_packets_default, "All packets should be delivered")
        self.assertEqual(self.tx.tx_next, self.rx.rx_deliv, "TX_NEXT and RX_DELIV should match")
        self.assertEqual(stats["discarded_duplicates"], 0)
        self.assertEqual(stats["discarded_old"], 0)
        self.assertEqual(stats["discarded_corrupted"], 0)
        self.assertEqual(stats["out_of_order_deliveries"], 0)

    def test_single_loss(self):
        self.channel.loss_rate = 0 # Base
        num_packets = 4
        
        # Manually lose one packet, e.g. SDU ID 3 (COUNT 3)
        lost_sdu_id = 3 
        original_transmit = self.channel.transmit
        
        def custom_transmit_for_loss(pdu_list):
            if pdu_list and pdu_list[0].sdu_id == lost_sdu_id:
                self.channel.stats["total_lost"] +=1
                return [] # Lose this packet
            return original_transmit(pdu_list) # Normal processing for others
        
        self.channel.transmit = custom_transmit_for_loss
        
        self._run_loop(num_packets, self.tx, self.channel, self.rx)
        self.channel.transmit = original_transmit # Restore original method

        stats = self.rx.get_status()
        self.assertEqual(stats["delivered_sdu_count"], num_packets -1 , "One packet should be lost")
        self.assertNotIn(lost_sdu_id, self.rx.delivered_sdu_ids)
        # RX_DELIV will stall at the lost packet's COUNT
        self.assertEqual(self.rx.rx_deliv, lost_sdu_id, f"RX_DELIV should be stalled at COUNT {lost_sdu_id}")


    def test_single_duplicate(self):
        self.channel.duplication_rate = 0 # Base
        num_packets = 10
        duplicated_sdu_id = 4

        original_transmit = self.channel.transmit
        has_duplicated = False
        def custom_transmit_for_duplication(pdu_list):
            nonlocal has_duplicated
            output = original_transmit(pdu_list) # Get normal output (original might be there)
            if pdu_list and pdu_list[0].sdu_id == duplicated_sdu_id and not has_duplicated:
                # Add a duplicate of the PDU that would have been output
                if output: # If not lost by other means
                    output.append(dataclasses.replace(output[0])) 
                    self.channel.stats["total_duplicated"] +=1
                    has_duplicated = True
            return output

        self.channel.transmit = custom_transmit_for_duplication
        self._run_loop(num_packets, self.tx, self.channel, self.rx)
        self.channel.transmit = original_transmit

        stats = self.rx.get_status()
        self.assertEqual(stats["delivered_sdu_count"], num_packets, "All unique packets should be delivered")
        self.assertEqual(stats["discarded_duplicates"], 1, "One duplicate should be discarded")
        self.assertEqual(self.tx.tx_next, self.rx.rx_deliv)


    def test_simple_reordering(self):
        # Packets 0, 1, 2, 3, 4. Send 2, then 0, then 1, then 3, 4.
        num_packets = 5
        
        # Override channel transmit to manually reorder
        pdus_to_send_ordered = []
        for i in range(num_packets):
            pdu = self.tx.send_sdu(sdu_id=i, sdu_payload=f"data_{i}")
            pdus_to_send_ordered.append(pdu)
        
        # Simulate reordering: e.g., PDU for SDU_ID 1 arrives after SDU_ID 2
        # Original order: P0, P1, P2, P3, P4
        # Reordered:     P0, P2, P1, P3, P4
        reordered_pdus_for_channel = [
            pdus_to_send_ordered[0], # P0
            pdus_to_send_ordered[2], # P2
            pdus_to_send_ordered[1], # P1
            pdus_to_send_ordered[3], # P3
            pdus_to_send_ordered[4]  # P4
        ]

        for pdu in reordered_pdus_for_channel:
            # Channel itself has no impairments for this test
            pdus_from_channel = self.channel.transmit([pdu])
            for p_out_ch in pdus_from_channel:
                self.rx.receive_pdu(p_out_ch)
        self.rx.flush_buffer()

        stats = self.rx.get_status()
        self.assertEqual(stats["delivered_sdu_count"], num_packets, "All packets should be delivered")
        self.assertEqual(self.tx.tx_next, self.rx.rx_deliv, "TX_NEXT and RX_DELIV should match after reordering handled")
        # Verify in-order delivery
        self.assertEqual(list(sorted(self.rx.delivered_sdu_ids)), list(range(num_packets)))


    def test_sn_wrap_around_clean(self):
        self.tx = PDCPTransmitter(sn_length=self.sn_length) # Reset TX
        self.rx = PDCPReceiver(sn_length=self.sn_length, t_reordering_threshold=sim_config.T_REORDERING_THRESHOLD) # Reset RX
        self.channel.loss_rate = 0 # No impairments

        # For 12-bit SN (0-4095), send > 4096 packets
        num_packets_for_wrap = (2**self.sn_length) + 100 
        self._run_loop(num_packets_for_wrap, self.tx, self.channel, self.rx)

        stats = self.rx.get_status()
        self.assertEqual(stats["delivered_sdu_count"], num_packets_for_wrap)
        self.assertEqual(self.tx.tx_next, self.rx.rx_deliv)
        self.assertTrue(self.tx.tx_next > (2**self.sn_length), "TX_NEXT should have wrapped COUNT")
        self.assertTrue(self.rx.rx_deliv > (2**self.sn_length), "RX_DELIV should have wrapped COUNT")


    def test_t_reordering_timer_expiry(self):
        self.rx = PDCPReceiver(sn_length=self.sn_length, t_reordering_threshold=3) # Small threshold
        num_packets = 10
        lost_sdu_id = 2 # Lose SDU 2 (COUNT 2)

        # Simulate transmission
        for i in range(num_packets):
            pdu = self.tx.send_sdu(sdu_id=i, sdu_payload=f"data_{i}")
            
            if pdu.sdu_id == lost_sdu_id:
                # print(f"Test: Losing PDU for SDU_ID {pdu.sdu_id}")
                continue # Skip sending this PDU to receiver

            # No other channel impairments
            pdus_from_channel = self.channel.transmit([pdu])
            for p_out_ch in pdus_from_channel:
                # print(f"Test: RX receives PDU for SDU_ID {p_out_ch.sdu_id}, COUNT {self.tx.tx_next-1 if p_out_ch.sdu_id == i else '???'}")
                self.rx.receive_pdu(p_out_ch)
        
        self.rx.flush_buffer()
        stats = self.rx.get_status()

        # Expected: SDU 0, 1 delivered. SDU 2 lost.
        # Timer starts when SDU 3 arrives (detects gap for SDU 2).
        # SDU 3, 4, 5 arrive. Threshold is 3. Timer expires.
        # SDUs 3, 4, 5 (and any other buffered before rx_next) should be delivered out of order.
        # RX_DELIV should then advance past the gap.
        self.assertIn(0, self.rx.delivered_sdu_ids)
        self.assertIn(1, self.rx.delivered_sdu_ids)
        self.assertNotIn(lost_sdu_id, self.rx.delivered_sdu_ids) # SDU 2 is lost
        
        # After timer expiry, SDUs 3, 4, ... up to 9 should be delivered
        for i in range(lost_sdu_id + 1, num_packets):
            self.assertIn(i, self.rx.delivered_sdu_ids, f"SDU {i} should be delivered after timer expiry")

        self.assertEqual(stats["delivered_sdu_count"], num_packets - 1)
        self.assertTrue(stats["out_of_order_deliveries"] > 0, "Some packets should be delivered out of order")
        # RX_DELIV should be TX_NEXT because all subsequent packets were delivered after timer expiry
        self.assertEqual(self.rx.rx_deliv, self.tx.tx_next, "RX_DELIV should advance to TX_NEXT after expiry and flush")

    def test_loss_reorder_across_wrap_around(self):
        # This is a complex scenario. We need enough packets for SN wrap.
        # And specific loss/reordering around the wrap point.
        sn_len = 3 # Very small SN (0-7) for quick wrap, Window=4
        modulus = 2**sn_len
        self.tx = PDCPTransmitter(sn_length=sn_len)
        self.rx = PDCPReceiver(sn_length=sn_len, t_reordering_threshold=5)
        self.channel.loss_rate = 0 # Control impairments manually

        # Packets to send: 0..15 (two full SN cycles and a bit more)
        # HFN 0: SN 0..7 (COUNT 0..7)
        # HFN 1: SN 0..7 (COUNT 8..15)
        # HFN 2: SN 0..X (COUNT 16..)
        num_total_packets = 2 * modulus + 4 # e.g., 16+4 = 20 packets for SN=3

        all_pdus = []
        for i in range(num_total_packets):
            all_pdus.append(self.tx.send_sdu(sdu_id=i, sdu_payload=f"data_{i}"))

        # Scenario:
        # 1. Packet COUNT=6 (HFN0, SN6) is lost.
        # 2. Packet COUNT=7 (HFN0, SN7) arrives.
        # 3. Packet COUNT=8 (HFN1, SN0) arrives. RX_DELIV is at 6. Buffer has 7, 8.
        # 4. Packet COUNT=5 (HFN0, SN5), which was delayed, arrives *late*.
        #    RX_DELIV is 6. HFN calc for SN5 with RX_DELIV=(HFN0,SN6) should be HFN0. COUNT=5.
        #    This should be discarded as old (COUNT 5 < RX_DELIV 6).
        #
        # Let's refine:
        # Target: Test late packet from previous HFN cycle when RX_DELIV has advanced into current HFN.
        # RX_DELIV = (HFN=1, SN=2) (i.e. COUNT = modulus + 2)
        # A late packet arrives: PDU with (HFN=0, SN=modulus-1) (i.e. COUNT = modulus-1)
        # This late packet's SN is modulus-1. sn_rx_deliv is 2.
        # HFN calc for SN=modulus-1:
        #   modulus-1 < 2 - WindowSize (e.g. 7 < 2 - 4 = -2) -> FALSE
        #   modulus-1 >= 2 + WindowSize (e.g. 7 >= 2 + 4 = 6) -> TRUE
        #   So derived HFN = HFN(RX_DELIV) - 1 = 1 - 1 = 0.
        #   Reconstructed COUNT = (0 << sn_len) | (modulus-1) = modulus-1.
        #   This COUNT = modulus-1 should be < RX_DELIV = modulus+2. So discard as old.

        # Setup state:
        # Send packets 0 to modulus+1 (e.g., 0-9 for SN=3) normally.
        # RX_DELIV will be modulus+2. (e.g. 10)
        for i in range(modulus + 2): # SDU_IDs 0 to modulus+1
            pdu = all_pdus[i]
            for p_out_ch in self.channel.transmit([pdu]):
                self.rx.receive_pdu(p_out_ch)
        
        self.assertEqual(self.rx.rx_deliv, modulus + 2) # e.g. COUNT 10 if modulus is 8
        self.assertEqual(self.rx.rx_deliv >> sn_len, 1, "RX_DELIV should be in HFN 1")

        # Now, a late packet from HFN0 arrives: PDU for SDU_ID = modulus-1 (e.g. 7)
        # This PDU has SN = modulus-1, original COUNT = modulus-1
        late_pdu = all_pdus[modulus - 1] 
        self.assertEqual(late_pdu.sn, modulus - 1)
        self.assertEqual(late_pdu.count >> sn_len, 0, "Late PDU should be from HFN 0")

        # Receiver processes this late PDU
        initial_discarded_old = self.rx.get_status()["discarded_old"]
        for p_out_ch in self.channel.transmit([late_pdu]): # Channel itself has no impairments
            self.rx.receive_pdu(p_out_ch)
        
        final_discarded_old = self.rx.get_status()["discarded_old"]
        self.assertEqual(final_discarded_old, initial_discarded_old + 1, "Late packet from previous HFN cycle should be discarded as old")
        self.assertEqual(self.rx.rx_deliv, modulus + 2, "RX_DELIV should not change due to old packet")
        
        # Continue sending remaining packets
        for i in range(modulus + 2, num_total_packets):
            pdu = all_pdus[i]
            for p_out_ch in self.channel.transmit([pdu]):
                self.rx.receive_pdu(p_out_ch)
        self.rx.flush_buffer()

        stats = self.rx.get_status()
        self.assertEqual(stats["delivered_sdu_count"], num_total_packets -1 ) # -1 because the late one was discarded and not redelivered.
        self.assertEqual(self.rx.rx_deliv, num_total_packets)


if __name__ == '__main__':
    # If you want to run tests with more verbose logging from the main modules:
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    # logging.getLogger('src.pdcp_entity').setLevel(logging.DEBUG)

    # For standard test output:
    logging.basicConfig(level=logging.WARNING) # Suppress info/debug from modules unless a test fails
    unittest.main()