class PDCP_PDU:
    def __init__(self, sn: int, hfn: int, count: int, payload: bytes, is_corrupted: bool = False):
        self.sn = sn
        self.hfn = hfn
        self.count = count
        self.payload = payload
        self.is_corrupted = is_corrupted
        self.deciphered_payload = None
        self.verified_integrity = False