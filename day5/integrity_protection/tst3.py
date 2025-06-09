import hmac
import hashlib
#to detect for duplicates...
# Simulated parameters
key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")  #secret code for reciver and sender
count = 0x00000001 #uniq code for packet
bearer = 0x01 #bearer id
direction = 0x00 #0 for uplink 1 for downlink
message = b"Hello, 5G World!"

# Store received COUNTs (simulating receiver's state)
received_counts = set()     # creates an empty set for reciever

# Compute MAC-I
def compute_mac_i(key, count, bearer, direction, message):   #this func is used to compute mac_i
    input_data = (
        count.to_bytes(4, byteorder="big")
        + bearer.to_bytes(1, byteorder="big")
        + direction.to_bytes(1, byteorder="big")
        + message
    )
    return hmac.new(key, input_data, hashlib.sha256).digest()[:4]

# First PDU: Valid
mac_i = compute_mac_i(key, count, bearer, direction, message)     #sender mac i
if count not in received_counts:
    received_counts.add(count)
    print("Test Case 3: First PDU")
    print(f"COUNT: {count}, MAC-I: {mac_i.hex()}")
    print("Result: Accepted")
else:
    print("Result: Rejected (Replay detected)")

# Replay PDU: Same COUNT 
count = 0x00000001  # Reusing COUNT    #again sending same count 
mac_i = compute_mac_i(key, count, bearer, direction, message)
if count not in received_counts:
    received_counts.add(count)
    print("Test Case 3: Replay PDU")
    print(f"COUNT: {count}, MAC-I: {mac_i.hex()}")
    print("Result: Accepted")
else:
    print("Test Case 3: Replay PDU")
    print(f"COUNT: {count}, MAC-I: {mac_i.hex()}")
    print("Result: Rejected (Replay detected)")