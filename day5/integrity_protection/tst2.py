import hmac
import hashlib
# to detect how code runs when any packet is tamperd .
# Simulated parameters (same as Test Case 1)
key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")  # secret code for both sendder and reciver 
count = 0x00000001   # uniq for packet
bearer = 0x01 #barer id
direction = 0x00  # 0 for uplink 1 for downlink
message = b"Hello, 5G World!"

# Compute MAC-I
def compute_mac_i(key, count, bearer, direction, message):  #this func computes mac i
    input_data = (
        count.to_bytes(4, byteorder="big")
        + bearer.to_bytes(1, byteorder="big")
        + direction.to_bytes(1, byteorder="big")
        + message
    )
    return hmac.new(key, input_data, hashlib.sha256).digest()[:4]

# Sender: Compute MAC-I
mac_i = compute_mac_i(key, count, bearer, direction, message)

# Receiver: Simulate tampering
received_mac_i = bytes.fromhex("ffffffff")  # Tampered MAC-I   #sender mac i
computed_mac_i = compute_mac_i(key, count, bearer, direction, message) # reciever mac i
is_valid = hmac.compare_digest(received_mac_i, computed_mac_i)

# Output
print("Test Case 2: Tampered MAC-I Field")
print(f"Computed MAC-I: {computed_mac_i.hex()}")
print(f"Received MAC-I: {received_mac_i.hex()}")
print(f"Verification: {'Pass' if is_valid else 'Fail'}")