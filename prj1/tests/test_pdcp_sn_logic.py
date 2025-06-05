import unittest
from src.pdcp_entity import PDCPReceiver

class TestPDCPReceiverHFNCalculation(unittest.TestCase):

    def setUp(self):
        # Default receiver for 12-bit SN
        self.receiver_12bit = PDCPReceiver(sn_length=12, t_reordering_threshold=10)
        self.mod_12bit = 2**12
        self.win_12bit = 2**(12 - 1)

        # Default receiver for 18-bit SN
        self.receiver_18bit = PDCPReceiver(sn_length=18, t_reordering_threshold=10)
        self.mod_18bit = 2**18
        self.win_18bit = 2**(18-1)

    def _test_hfn_calc(self, receiver, rx_deliv_val, rcvd_sn_val, expected_hfn_offset):
        """Helper to test HFN calculation.
        expected_hfn_offset is 0 for same HFN, +1 for next, -1 for previous.
        """
        receiver.rx_deliv = rx_deliv_val
        hfn_rx_deliv = rx_deliv_val >> receiver.sn_length
        
        derived_hfn = receiver._calculate_hfn_from_rcvd_sn(rcvd_sn_val)
        expected_full_hfn = hfn_rx_deliv + expected_hfn_offset
        
        # print(f"Test: RX_DELIV={rx_deliv_val} (SN={rx_deliv_val % receiver.modulus}, HFN={hfn_rx_deliv}), Rcvd SN={rcvd_sn_val} -> Derived HFN={derived_hfn}, Expected HFN={expected_full_hfn}")
        self.assertEqual(derived_hfn, expected_full_hfn, 
                         f"RX_DELIV={rx_deliv_val} (SN={rx_deliv_val % receiver.modulus}, HFN={hfn_rx_deliv}), "
                         f"Rcvd SN={rcvd_sn_val}. Expected HFN {expected_full_hfn}, Got {derived_hfn}")

    # --- 12-bit SN Tests ---
    def test_12bit_no_wrap_around_center_window(self):
        # RX_DELIV = HFN 0, SN 100
        # Window [100-2048, 100+2048-1] around SN 100
        # Effectively, SNs from previous HFN (e.g. 2048+100 = 2148) to next HFN (e.g. 100-2048 = -1948, so small SNs)
        rx_deliv_val = 100 
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=150, expected_hfn_offset=0) # Within window
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=50, expected_hfn_offset=0)  # Within window

    def test_12bit_approaching_wrap_rx_deliv_high_sn(self):
        # RX_DELIV = HFN 0, SN 4000
        # Window around SN 4000. SNs slightly larger (e.g. 4050) are same HFN.
        # SNs much smaller (e.g. 100) are HFN+1.
        rx_deliv_val = 4000 
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=4050, expected_hfn_offset=0) # 4050 in [4000-2048, 4000+2048-1] = [1952, 6047] -> [1952, 4095]U[0, 1951]
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=100, expected_hfn_offset=1)   # 100 < 4000 - 2048 (1952) -> HFN+1
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=2000, expected_hfn_offset=0) # 2000 > 1952. Stays HFN 0.

    def test_12bit_after_wrap_rx_deliv_low_sn_hfn_gt_0(self):
        # RX_DELIV = HFN 1, SN 100. (COUNT = 4096 + 100 = 4196)
        # Window around SN 100. SNs slightly smaller (e.g. 50) are same HFN.
        # SNs much larger (e.g. 4000) are HFN-1.
        rx_deliv_val = self.mod_12bit * 1 + 100 
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=50, expected_hfn_offset=0)    # 50 in [100-2048, 100+2048-1] with HFN 1.
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=4000, expected_hfn_offset=-1) # 4000 >= 100 + 2048 (2148) -> HFN-1
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=2000, expected_hfn_offset=0)  # 2000 < 2148. Stays HFN 1.

    def test_12bit_edge_cases_window_boundaries(self):
        # RX_DELIV = HFN 0, SN 2048 (Window middle for SN space)
        # Window = [2048-2048, 2048+2048-1] = [0, 4095].
        # So SNs < 0 (impossible) implies HFN+1. SNs >= 4096 (impossible) implies HFN-1.
        # The condition is rcvd_sn < sn_rx_deliv - Window_Size.
        # sn_rx_deliv - Window_Size = 2048 - 2048 = 0.
        # rcvd_sn < 0 -> HFN+1.
        # The condition is rcvd_sn >= sn_rx_deliv + Window_Size.
        # sn_rx_deliv + Window_Size = 2048 + 2048 = 4096.
        # rcvd_sn >= 4096 -> HFN-1.
        # For SN=0, HFN=0
        # For SN=4095, HFN=0
        rx_deliv_val = 2048 
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=0, expected_hfn_offset=0) 
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=self.max_12bit_sn, expected_hfn_offset=0)

        # RX_DELIV = HFN 0, SN 0
        # sn_rx_deliv - Window_Size = 0 - 2048 = -2048
        # rcvd_sn < -2048 (impossible for positive SNs) -> HFN+1
        # sn_rx_deliv + Window_Size = 0 + 2048 = 2048
        # rcvd_sn >= 2048 -> HFN-1 (meaning from previous HFN cycle, i.e. HFN becomes -1 if current HFN is 0)
        rx_deliv_val = 0 
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=10, expected_hfn_offset=0)
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=2047, expected_hfn_offset=0) # 2047 is not >= 2048
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=2048, expected_hfn_offset=-1) # 2048 is >= 2048
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=4000, expected_hfn_offset=-1) # 4000 is >= 2048

        # RX_DELIV = HFN 1, SN 0 (COUNT = 4096)
        rx_deliv_val = self.mod_12bit
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=2047, expected_hfn_offset=0) # HFN = 1
        self._test_hfn_calc(self.receiver_12bit, rx_deliv_val, rcvd_sn_val=2048, expected_hfn_offset=-1) # HFN = 1-1 = 0

    # --- 18-bit SN Tests (similar logic, different constants) ---
    @property
    def max_12bit_sn(self):
        return self.mod_12bit - 1
        
    @property
    def max_18bit_sn(self):
        return self.mod_18bit - 1

    def test_18bit_no_wrap_around_center_window(self):
        rx_deliv_val = 1000 
        self._test_hfn_calc(self.receiver_18bit, rx_deliv_val, rcvd_sn_val=1500, expected_hfn_offset=0)
        self._test_hfn_calc(self.receiver_18bit, rx_deliv_val, rcvd_sn_val=500, expected_hfn_offset=0)

    def test_18bit_approaching_wrap_rx_deliv_high_sn(self):
        rx_deliv_val = self.max_18bit_sn - 1000
        self._test_hfn_calc(self.receiver_18bit, rx_deliv_val, rcvd_sn_val=rx_deliv_val + 50, expected_hfn_offset=0)
        self.receiver_18bit.rx_deliv = rx_deliv_val # reset rx_deliv for next sub-test
        self._test_hfn_calc(self.receiver_18bit, rx_deliv_val, rcvd_sn_val=100, expected_hfn_offset=1)

    def test_18bit_after_wrap_rx_deliv_low_sn_hfn_gt_0(self):
        rx_deliv_val = self.mod_18bit * 1 + 1000
        self._test_hfn_calc(self.receiver_18bit, rx_deliv_val, rcvd_sn_val=500, expected_hfn_offset=0)
        self.receiver_18bit.rx_deliv = rx_deliv_val # reset rx_deliv for next sub-test
        self._test_hfn_calc(self.receiver_18bit, rx_deliv_val, rcvd_sn_val=self.max_18bit_sn - 500, expected_hfn_offset=-1)

if __name__ == '__main__':
    unittest.main()