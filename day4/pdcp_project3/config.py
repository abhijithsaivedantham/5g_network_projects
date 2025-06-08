# Configuration parameters for PDCP simulation
CIPHERING_ENABLED = True
CIPHER_KEY_LENGTH_BYTES = 16
INTEGRITY_ENABLED_FOR_DRB = True
TAMPERING_RATE = 0.01  # Probability of packet tampering in channel
SN_LENGTH = 12  # 12-bit SN for simulation
MAX_SN = 2**SN_LENGTH - 1