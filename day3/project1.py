# --- Constants for SDAP Header (Simplified for 1-byte header) ---
UL_DC_DATA = 0b10000000  # D = 1 (Data), R = 0
UL_QFI_MASK = 0b00111111  # 6-bit QFI mask

class SDAPEntity:
    """
    Simplified SDAP Entity to simulate uplink and downlink SDAP PDU handling.
    """
    def __init__(self):
        self.default_drb = 1
        self.drb_config = {
            1: {'has_sdap_header': True}
        }
        print("[Init] SDAP Entity created.")

    def _pack_ul_sdap_header(self, qos_flow_id):
        """Pack 1-byte uplink SDAP header."""
        return bytes([UL_DC_DATA | (qos_flow_id & UL_QFI_MASK)])

    def _parse_ul_sdap_header(self, header_byte):
        """Parse 1-byte uplink SDAP header."""
        d_c = (header_byte & 0b10000000) >> 7
        r_bit = (header_byte & 0b01000000) >> 6
        qfi = header_byte & UL_QFI_MASK
        return d_c, r_bit, qfi

    def build_sdap_pdu(self, qos_flow_id, sdu_data):
        """Construct an SDAP PDU for uplink."""
        sdu_bytes = sdu_data.encode('utf-8')
        sdap_header = self._pack_ul_sdap_header(qos_flow_id)
        return sdap_header + sdu_bytes

    def decode_sdap_pdu(self, sdap_pdu):
        """Decode a received SDAP PDU for downlink."""
        header_byte = sdap_pdu[0]
        d_c, r_bit, qfi = self._parse_ul_sdap_header(header_byte)
        payload = sdap_pdu[1:].decode('utf-8')
        return header_byte, d_c, r_bit, qfi, payload

def run_project_1():
    print("--- Project 1: SDAP_PDU_Builder_And_Decoder ---")

    # Initialize SDAP Entity
    sdap = SDAPEntity()

    # Define QoS Flow ID and original message
    qos_flow_id = 9
    original_payload = "Hello 5G SDAP!"

    # Build SDAP PDU
    sdap_pdu = sdap.build_sdap_pdu(qos_flow_id, original_payload)
    print(f"\nSDAP PDU (hex): {sdap_pdu.hex().upper()}")

    # Decode SDAP PDU
    header_byte, d_c, r_bit, qfi, payload = sdap.decode_sdap_pdu(sdap_pdu)
    print(f"Header Byte: {bin(header_byte >> 6)}")  # Show only D/C and R bits (first 2 bits)
    print(f"QFI: {qfi}")
    print(f"Payload: {payload}")

    print("\n--- Project 1 Completed ---")

# Run the project
if __name__ == "__main__":
    run_project_1()
