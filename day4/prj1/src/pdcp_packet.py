import dataclasses

@dataclasses.dataclass
class PDCP_SDU:
    id: int  # Unique identifier for the SDU
    payload: str  # Actual data (simple string for simulation)

@dataclasses.dataclass
class PDCP_PDU:
    sdu_id: int  # Reference to the original SDU's id
    sn: int  # PDCP Sequence Number (12-bit or 18-bit)
    count: int  # Full 32-bit COUNT value (for internal tracking at Tx, and verification)
    hfn: int  # HFN part of the COUNT (for internal tracking/display)
    original_sdu_payload: str  # The original SDU payload
    is_corrupted: bool = False

    def __str__(self):
        return f"PDU(sdu_id={self.sdu_id}, SN={self.sn}, COUNT={self.count}, HFN={self.hfn}, corrupted={self.is_corrupted})"

    # For duplicate checking in sets if needed, though we primarily use COUNT
    def __hash__(self):
        return hash((self.sdu_id, self.sn, self.count, self.original_sdu_payload, self.is_corrupted))