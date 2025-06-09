import hmac
import hashlib
# doing verification for boundary count values
# Simulated parameters
key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF") #uniq for send and rec
bearer = 0x01 #barer id
direction = 0x00 #0 for up 1 for down
message = b"Hello, 5G World!"

# Compute MAC-I
def compute_mac_i(key, count, bearer, direction, message):    #this func is used to compute maci
    input_data = (
        count.to_bytes(4, byteorder="big")
        + bearer.to_bytes(1, byteorder="big")
        + direction.to_bytes(1, byteorder="big")
        + message
    )
    return hmac.new(key, input_data, hashlib.sha256).digest()[:4]

# Test boundary COUNT values
counts = [0x00000000, 0xFFFFFFFF]  # Min and max 32-bit COUNT    # here 2 mac i are createed for min and max count
for count in counts:
    mac_i = compute_mac_i(key, count, bearer, direction, message)
    print(f"Test Case 4: COUNT = {count:08x}")
    print(f"MAC-I: {mac_i.hex()}")
    print("Result: Pass (MAC-I computed successfully)")   