from pdcp_packet import PDCP_PDU
from crypto_stub import encrypt, decrypt
from config import SN_LENGTH, MAX_SN

class PDCPTransmitter:
    def __init__(self, bearer_id: int, direction: int, cipher_key: bytes, ciphering_enabled: bool):
        self.bearer_id = bearer_id
        self.direction = direction
        self.cipher_key = cipher_key
        self.ciphering_enabled = ciphering_enabled
        self.tx_next = 0

    def send_sdu(self, sdu_payload: bytes):
        hfn = self.tx_next >> SN_LENGTH
        sn = self.tx_next & MAX_SN
        count = self.tx_next
        payload_to_cipher = sdu_payload
        if self.ciphering_enabled:
            ciphered_payload = encrypt(self.cipher_key, count, self.bearer_id, self.direction, payload_to_cipher)
        else:
            ciphered_payload = payload_to_cipher
        pdu = PDCP_PDU(sn, hfn, count, ciphered_payload)
        self.tx_next = (self.tx_next + 1) % (2 ** 32)
        return pdu

class PDCPReceiver:
    def __init__(self, bearer_id: int, direction: int, cipher_key: bytes, ciphering_enabled: bool):
        self.bearer_id = bearer_id
        self.direction = direction
        self.cipher_key = cipher_key
        self.ciphering_enabled = ciphering_enabled
        self.rx_deliv = 0

    def receive_pdu(self, pdu):
        if pdu.is_corrupted:
            return None
        rcvd_count = (pdu.hfn << SN_LENGTH) | pdu.sn
        if self.ciphering_enabled:
            deciphered_payload = decrypt(self.cipher_key, rcvd_count, self.bearer_id, self.direction, pdu.payload)
        else:
            deciphered_payload = pdu.payload
        pdu.deciphered_payload = deciphered_payload
        pdu.verified_integrity = True
        return deciphered_payload