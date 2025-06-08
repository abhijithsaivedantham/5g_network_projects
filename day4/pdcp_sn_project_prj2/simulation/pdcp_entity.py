from . import crypto_logic

class PDCP_PDU:
    """A simple class to represent a PDCP Packet Data Unit."""
    def __init__(self, sdu_id, count, payload, mac_i=None):
        self.sdu_id = sdu_id
        self.count = count
        self.payload = payload
        self.mac_i = mac_i

class PDCPTransmitter:
    """Simulates the transmitting side of a PDCP entity."""
    def __init__(self, integrity_key, bearer_id, direction):
        self.integrity_key = integrity_key
        self.bearer_id = bearer_id
        self.direction = direction
        self.count = 0

    def send_sdu(self, sdu_payload: bytes):
        self.count += 1
        
        # 1. Calculate MAC-I
        mac_i = crypto_logic.calculate_mac_i(
            self.integrity_key,
            self.count,
            self.bearer_id,
            self.direction,
            sdu_payload
        )
        
        # 2. Create PDU
        pdu = PDCP_PDU(sdu_id=self.count, count=self.count, payload=sdu_payload, mac_i=mac_i)
        
        log_entry = {
            "event": "tx_protect",
            "sdu_id": pdu.sdu_id,
            "count": hex(pdu.count),
            "payload": pdu.payload.decode(),
            "mac_i": pdu.mac_i.hex()
        }
        
        return pdu, log_entry

class PDCPReceiver:
    """Simulates the receiving side of a PDCP entity."""
    def __init__(self, integrity_key, bearer_id, direction):
        self.integrity_key = integrity_key
        self.bearer_id = bearer_id
        self.direction = direction
        self.delivered_sdu_count = 0
        self.discarded_pdu_count = 0

    def receive_pdu(self, pdu: PDCP_PDU):
        # 1. Recalculate MAC-I (called X-MAC in 3GPP)
        calculated_x_mac = crypto_logic.calculate_mac_i(
            self.integrity_key,
            pdu.count,
            self.bearer_id,
            self.direction,
            pdu.payload
        )

        # 2. Verify Integrity
        if calculated_x_mac == pdu.mac_i:
            # Integrity check passed
            self.delivered_sdu_count += 1
            log_entry = {
                "event": "rx_verify_pass",
                "sdu_id": pdu.sdu_id,
                "received_mac": pdu.mac_i.hex(),
                "calculated_x_mac": calculated_x_mac.hex(),
                "status": "PASSED"
            }
            return True, log_entry
        else:
            # Integrity check failed
            self.discarded_pdu_count += 1
            log_entry = {
                "event": "rx_verify_fail",
                "sdu_id": pdu.sdu_id,
                "received_mac": pdu.mac_i.hex(),
                "calculated_x_mac": calculated_x_mac.hex(),
                "status": "FAILED"
            }
            return False, log_entry