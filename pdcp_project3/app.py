from flask import Flask, render_template, request, jsonify
from pdcp_entity import PDCPTransmitter, PDCPReceiver
from channel_simulator import ChannelSimulator
from crypto_stub import generate_cipher_key, encrypt, decrypt
from config import CIPHERING_ENABLED

# No longer need matplotlib here
# import matplotlib
# matplotlib.use('Agg')  # Use non-interactive backend
# import matplotlib.pyplot as plt
# import os

app = Flask(__name__, static_folder="static", template_folder="templates")

# These instances are created for each user session in a real app.
# For this demo, we initialize them once.
cipher_key = generate_cipher_key()
transmitter = PDCPTransmitter(bearer_id=5, direction=0, cipher_key=cipher_key, ciphering_enabled=CIPHERING_ENABLED)
receiver = PDCPReceiver(bearer_id=5, direction=0, cipher_key=cipher_key, ciphering_enabled=CIPHERING_ENABLED)
channel = ChannelSimulator()
wrong_key = generate_cipher_key()

# State (counters) is now managed on the client-side (in script.js)
# So we remove global counters from the server.

@app.route('/')
def index():
    # Reset the simulation state on page load for a clean start
    global transmitter, receiver
    transmitter = PDCPTransmitter(bearer_id=5, direction=0, cipher_key=cipher_key, ciphering_enabled=CIPHERING_ENABLED)
    receiver = PDCPReceiver(bearer_id=5, direction=0, cipher_key=cipher_key, ciphering_enabled=CIPHERING_ENABLED)
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        plaintext = request.form['plaintext'].encode()
        print(f"Received plaintext: {plaintext}")

        # 1. Transmitter creates and ciphers the PDU
        pdu = transmitter.send_sdu(plaintext)
        print(f"PDU created: SN={pdu.sn}, HFN={pdu.hfn}, Payload={pdu.payload.hex()}")

        # 2. Channel may corrupt the PDU
        transmitted_pdu = channel.transmit(pdu)
        print(f"Transmitted PDU: Corrupted={transmitted_pdu.is_corrupted}")

        # 3. Receiver deciphers the PDU
        deciphered = receiver.receive_pdu(transmitted_pdu)
        print(f"Deciphered: {deciphered}")

        # 4. Eavesdropper with wrong key tries to decipher
        ciphertext_hex = pdu.payload.hex()
        eavesdrop_attempt = decrypt(wrong_key, pdu.count, 5, 0, pdu.payload)
        eavesdrop_hex = eavesdrop_attempt.decode('utf-8', errors='replace')

        # Format results for JSON response
        deciphered_text = deciphered.decode('utf-8', errors='replace') if deciphered else 'Failed'
        plaintext_text = plaintext.decode('utf-8', errors='replace')

        # The plot generation is removed from the backend.
        # The frontend will handle all visualizations.

        response = {
            'plaintext': plaintext_text,
            'ciphertext': ciphertext_hex,
            'deciphered': deciphered_text,
            'eavesdrop': eavesdrop_hex
        }
        print(f"Sending response: {response}")
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in /simulate: {str(e)}")
        # It's good practice to log the full traceback for debugging
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)