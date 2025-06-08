from flask import Flask, render_template, request, jsonify
from simulation import crypto_logic, pdcp_entity, channel_simulator

app = Flask(__name__)

# --- Simulation Configuration ---
BEARER_ID = 5  # Example: Data Radio Bearer 5
UPLINK = 0
DOWNLINK = 1

@app.route('/')
def index():
    """Renders the main web page."""
    return render_template('index.html')

@app.route('/run_simulation', methods=['POST'])
def run_simulation():
    """Runs the PDCP integrity simulation and returns a log of events."""
    data = request.get_json()
    tamper_packet = data.get('tamper', False)
    
    # --- Setup ---
    # 1. Generate a shared integrity key for this simulation session
    integrity_key = crypto_logic.generate_integrity_key()
    
    # 2. Initialize PDCP entities (Transmitter and Receiver)
    pdcp_tx = pdcp_entity.PDCPTransmitter(integrity_key, BEARER_ID, UPLINK)
    pdcp_rx = pdcp_entity.PDCPReceiver(integrity_key, BEARER_ID, UPLINK) # Note: direction must match for shared context

    # 3. Prepare data to be sent
    sdu_payloads = [
        b"Control-Plane-Signal-01",
        b"Important-User-Data-Packet",
        b"Final-Transmission-Block"
    ]
    
    simulation_log = []
    
    # --- Simulation Loop ---
    for i, payload in enumerate(sdu_payloads):
        # 1. Transmitter: Protects the packet and creates a PDU
        pdu, tx_log = pdcp_tx.send_sdu(payload)
        simulation_log.append(tx_log)
        
        # 2. Channel: Optionally tamper with the packet
        # We tamper the packet with the target ID (in this case, the second packet)
        if tamper_packet and pdu.sdu_id == 2:
            pdu, tamper_log = channel_simulator.maliciously_tamper(pdu)
            simulation_log.append(tamper_log)
        else:
            simulation_log.append({"event": "channel_ok", "sdu_id": pdu.sdu_id})

        # 3. Receiver: Receives the PDU and performs integrity verification
        is_verified, rx_log = pdcp_rx.receive_pdu(pdu)
        simulation_log.append(rx_log)

    # --- Final Results ---
    results = {
        "packets_sent": len(sdu_payloads),
        "packets_delivered": pdcp_rx.delivered_sdu_count,
        "packets_discarded": pdcp_rx.discarded_pdu_count,
        "integrity_key": integrity_key.hex(),
        "bearer_id": BEARER_ID
    }

    return jsonify({
        "status": "success",
        "log": simulation_log,
        "results": results
    })

if __name__ == '__main__':
    app.run(debug=True)