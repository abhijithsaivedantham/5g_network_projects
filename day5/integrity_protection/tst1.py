import hmac
import hashlib
# how code runs if no tampering 
# Simulated parameters
key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")  # 128-bit key  #secret shared key btw sender and user
count = 0x00000001  # PDCP COUNT # unique no given to packet
bearer = 0x01  # Bearer ID 
direction = 0x00  # 0 for UpLink, 1 for DownLink
message = b"Hello, 5G World!"  # Sample PDCP payload

# Compute MAC-I (simplified, using HMAC-SHA256)
def compute_mac_i(key, count, bearer, direction, message):           #
    # Concatenate inputs as per 3GPP TS 33.501
    input_data = (
        count.to_bytes(4, byteorder="big")
        + bearer.to_bytes(1, byteorder="big")
        + direction.to_bytes(1, byteorder="big")
        + message
    )
    mac_i = hmac.new(key, input_data, hashlib.sha256).digest()[:4]  # Take first 4 bytes
    return mac_i

# Sender: Compute MAC-I
mac_i = compute_mac_i(key, count, bearer, direction, message)

# Receiver: Verify MAC-I
received_mac_i = mac_i  # Assume no tampering # sender mac i
computed_mac_i = compute_mac_i(key, count, bearer, direction, message)   # reciever mac i
is_valid = hmac.compare_digest(received_mac_i, computed_mac_i)

# Output
print("Test Case 1: Valid MAC-I Verification")
print(f"Computed MAC-I: {computed_mac_i.hex()}")
print(f"Received MAC-I: {received_mac_i.hex()}")
print(f"Verification: {'Pass' if is_valid else 'Fail'}")  # if both are same then case is passed