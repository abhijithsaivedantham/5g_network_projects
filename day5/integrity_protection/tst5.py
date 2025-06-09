import hmac
import hashlib
import random
# checking code if any bad signal(to get that func we r tampering the msg by applng xor oper)
# Simulated parameters
key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF") # uniq for sender and reciever
count = 0x00000001 #uniq fro packet
bearer = 0x01 # bearer id
direction = 0x00 # 0 for up 1 for down
message = b"RRC Connection Request"

# Simulate bit errors due to poor SINR
def simulate_bit_errors(message, error_rate=0.1): #      # this func is used to give error msg if there is any bad signl quality.
    message_bytes = bytearray(message)
    for i in range(len(message_bytes)):
        if random.random() < error_rate:
            message_bytes[i] ^= random.randint(0, 255)  # Flip bits
    return bytes(message_bytes)

# Compute MAC-I
def compute_mac_i(key, count, bearer, direction, message):        # this func is used to calculate mac i value
    input_data = (
        count.to_bytes(4, byteorder="big")
        + bearer.to_bytes(1, byteorder="big")
        + direction.to_bytes(1, byteorder="big")
        + message
    )
    return hmac.new(key, input_data, hashlib.sha256).digest()[:4]

# Sender: Compute MAC-I
mac_i = compute_mac_i(key, count, bearer, direction, message)    #sender mac i

# Receiver: Simulate poor SINR
received_message = simulate_bit_errors(message, error_rate=0.1)     #reciver side message
computed_mac_i = compute_mac_i(key, count, bearer, direction, received_message)     #resciver side mac i
is_valid = hmac.compare_digest(mac_i, computed_mac_i)

# Output
print("Test Case 5: Control Plane Message under Poor SINR")
print(f"Original Message: {message}")
print(f"Received Message: {received_message}")
print(f"Computed MAC-I: {computed_mac_i.hex()}")
print(f"Received MAC-I: {mac_i.hex()}")
print(f"Verification: {'Pass' if is_valid else 'Fail'}")