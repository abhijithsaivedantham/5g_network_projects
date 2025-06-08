import random

def maliciously_tamper(pdu):
    """Simulates a malicious actor flipping a bit in the payload."""
    payload_list = list(pdu.payload)
    if not payload_list:
        return pdu, None # Cannot tamper empty payload
        
    tamper_idx = random.randint(0, len(payload_list) - 1)
    original_char = payload_list[tamper_idx]
    
    # Flip a bit in the character's byte representation
    tampered_char_byte = bytes([original_char])
    tampered_byte = tampered_char_byte[0] ^ 0x01 # XOR to flip the least significant bit
    
    payload_list[tamper_idx] = tampered_byte
    
    pdu.payload = bytes(payload_list)
    
    log_entry = {
        "event": "channel_tamper",
        "sdu_id": pdu.sdu_id,
        "detail": f"Payload bit flipped at index {tamper_idx}."
    }
    
    return pdu, log_entry