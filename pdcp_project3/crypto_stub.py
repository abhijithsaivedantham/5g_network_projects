from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes

def generate_cipher_key(length_bytes=16):
    return get_random_bytes(length_bytes)

def _generate_key_stream(cipher_key: bytes, count: int, bearer: int, direction: int, length_needed: int) -> bytes:
    """
    Generates a key stream using AES in CTR mode, with COUNT, BEARER, DIRECTION
    as part of the nonce/initial counter block, similar to 3GPP.
    Returns a key stream of length_needed bytes.
    """
    # Construct a 7-byte nonce: COUNT (4 bytes) + BEARER (1 byte) + DIRECTION (1 byte) + padding (1 byte)
    count_bytes = count.to_bytes(4, 'big')
    bearer_byte = bearer.to_bytes(1, 'big')
    direction_byte = direction.to_bytes(1, 'big')
    nonce = count_bytes + bearer_byte + direction_byte + b'\x00' * 1  # Total 7 bytes

    # AES in CTR mode for key stream generation
    # Let pycryptodome handle the counter (remaining 9 bytes of the 16-byte block)
    cipher = AES.new(cipher_key, AES.MODE_CTR, nonce=nonce)

    # Generate enough key stream for the plaintext
    key_stream = cipher.encrypt(b'\x00' * length_needed)
    return key_stream

def encrypt(cipher_key: bytes, count: int, bearer: int, direction: int, plaintext: bytes) -> bytes:
    """
    Ciphering function: XORs plaintext with generated key stream.
    """
    key_stream = _generate_key_stream(cipher_key, count, bearer, direction, len(plaintext))
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, key_stream))
    return ciphertext

def decrypt(cipher_key: bytes, count: int, bearer: int, direction: int, ciphertext: bytes) -> bytes:
    """
    Deciphering function: XORs ciphertext with generated key stream.
    (Same operation as encrypt for stream ciphers like CTR).
    """
    key_stream = _generate_key_stream(cipher_key, count, bearer, direction, len(ciphertext))
    plaintext = bytes(c ^ k for c, k in zip(ciphertext, key_stream))
    return plaintext