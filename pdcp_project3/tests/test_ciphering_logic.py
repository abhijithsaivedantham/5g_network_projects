import unittest
from src.crypto_stub import generate_cipher_key, encrypt, decrypt

class TestCipheringLogic(unittest.TestCase):
    def test_encrypt_decrypt(self):
        key = generate_cipher_key()
        plaintext = b"Test message"
        count, bearer, direction = 12345, 5, 0
        ciphertext = encrypt(key, count, bearer, direction, plaintext)
        deciphered = decrypt(key, count, bearer, direction, ciphertext)
        self.assertEqual(plaintext, deciphered)

    def test_wrong_key(self):
        key1 = generate_cipher_key()
        key2 = generate_cipher_key()
        plaintext = b"Test message"
        count, bearer, direction = 12345, 5, 0
        ciphertext = encrypt(key1, count, bearer, direction, plaintext)
        deciphered = decrypt(key2, count, bearer, direction, ciphertext)
        self.assertNotEqual(plaintext, deciphered)

if __name__ == '__main__':
    unittest.main()