from Cryptodome.Cipher import AES
from Cryptodome.Hash import CMAC
from Cryptodome.Random import get_random_bytes

# Simulates generating a 128-bit integrity key
def generate_integrity_key(length_bytes=16):
    return get_random_bytes(length_bytes)

def calculate_mac_i(integrity_key: bytes, count: int, bearer: int, direction: int, input_data: bytes) -> bytes:
    """
    Simulates 3GPP integrity algorithm (e.g., EIA2/NIA2) using AES-CMAC.
    Returns 32-bit (4-byte) MAC-I.
    """
    # Combine inputs as per 3GPP TS 33.501 (simplified for simulation)
    # COUNT (4 bytes) | BEARER (1 byte) | DIRECTION (1 byte)
    count_bytes = count.to_bytes(4, 'big')
    bearer_byte = bearer.to_bytes(1, 'big')
    direction_byte = direction.to_bytes(1, 'big')
    
    # Message to be authenticated
    mac_input_block = count_bytes + bearer_byte + direction_byte + input_data

    # --- THIS IS THE CORRECTED PART ---
    # Use AES-CMAC for MAC calculation.
    # We pass the raw key and specify the cipher module with 'ciphermod'.
    mac_obj = CMAC.new(integrity_key, msg=mac_input_block, ciphermod=AES)
    
    # 3GPP specifies a 32-bit (4-byte) MAC-I, so we truncate the output
    full_mac = mac_obj.digest()
    mac_i = full_mac[:4] 
    return mac_i