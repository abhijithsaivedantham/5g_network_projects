import hmac
import hashlib
# End-to-end secure RRC Connection Setup flow

# Simulated parameters
key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")
bearer = 0x01
direction = 0x00
messages = [                                        # list of msgs exchange btn uE and gNb
    b"RRC Connection Request",
    b"RRC Connection Setup",
    b"RRC Connection Setup Complete"
]

# Compute MAC-I
def compute_mac_i(key, count, bearer, direction, message):
    input_data = (
        count.to_bytes(4, byteorder="big")
        + bearer.to_bytes(1, byteorder="big")
        + direction.to_bytes(1, byteorder="big")
        + message
    )
    return hmac.new(key, input_data, hashlib.sha256).digest()[:4]

# Simulate RRC Connection Setup flow
count = 0x00000001          #uniq id for packet
for msg in messages:
    mac_i = compute_mac_i(key, count, bearer, direction, msg)   
    received_mac_i = mac_i  # Assume no tampering
    is_valid = hmac.compare_digest(mac_i, received_mac_i)
    print(f"Test Case 6: RRC Message - {msg.decode()}")
    print(f"COUNT: {count:08x}, MAC-I: {mac_i.hex()}")
    print(f"Verification: {'Pass' if is_valid else 'Fail'}")
    count += 1  # Increment COUNT for each message