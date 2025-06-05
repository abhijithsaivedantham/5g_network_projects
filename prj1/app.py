from flask import Flask, render_template, request, jsonify
import io
import base64
import matplotlib
matplotlib.use('Agg') # Non-interactive backend for Matplotlib
import matplotlib.pyplot as plt
import os
from datetime import datetime
import logging

# Project modules
import config as default_config
from main import run_simulation # The core simulation logic from main.py
from src.pdcp_entity import PDCPTransmitter, PDCPReceiver # For type hints or direct use if needed
from src.channel_simulator import ImpairedChannel

app = Flask(__name__)

# Setup basic logging for the Flask app
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
app.logger.setLevel(logging.INFO)


class SimulationParameters:
    """Class to hold simulation parameters, similar to config module."""
    def __init__(self, **kwargs):
        self.SN_LENGTH_BITS = kwargs.get('SN_LENGTH_BITS', default_config.SN_LENGTH_BITS)
        self.SIMULATION_PACKETS = kwargs.get('SIMULATION_PACKETS', default_config.SIMULATION_PACKETS)
        self.LOSS_RATE = kwargs.get('LOSS_RATE', default_config.LOSS_RATE)
        self.REORDERING_RATE = kwargs.get('REORDERING_RATE', default_config.REORDERING_RATE)
        self.DUPLICATION_RATE = kwargs.get('DUPLICATION_RATE', default_config.DUPLICATION_RATE)
        self.CORRUPTION_RATE = kwargs.get('CORRUPTION_RATE', default_config.CORRUPTION_RATE)
        self.T_REORDERING_THRESHOLD = kwargs.get('T_REORDERING_THRESHOLD', default_config.T_REORDERING_THRESHOLD)
        self.PLOT_GRANULARITY = kwargs.get('PLOT_GRANULARITY', default_config.PLOT_GRANULARITY)
        self.LOG_LEVEL = kwargs.get('LOG_LEVEL', default_config.LOG_LEVEL)

def generate_plots_base64(plot_data):
    """Generates plots and returns them as base64 encoded strings."""
    plots_base64 = {}

    try:
        # Plot 1: TX_NEXT vs RX_DELIV vs RX_NEXT
        plt.figure(figsize=(10, 5)) # Adjusted size for web
        plt.plot(plot_data["time"], plot_data["tx_count"], label='TX_NEXT', linestyle='--')
        plt.plot(plot_data["time"], plot_data["rx_deliv"], label='RX_DELIV')
        plt.plot(plot_data["time"], plot_data["rx_next"], label='RX_NEXT', linestyle=':')
        plt.xlabel('Simulation Step (Packet Index)')
        plt.ylabel('COUNT Value')
        plt.title('PDCP COUNT Progression')
        plt.legend()
        plt.grid(True)
        plt.tight_layout() # Adjust layout
        
        img_io = io.BytesIO()
        plt.savefig(img_io, format='png', bbox_inches='tight')
        img_io.seek(0)
        plots_base64['count_progression'] = base64.b64encode(img_io.getvalue()).decode('utf-8')
        plt.close()

        # Plot 2: Reordering Buffer Size
        plt.figure(figsize=(10, 5))
        plt.plot(plot_data["time"], plot_data["buffer_size"], label='Reordering Buffer Size', color='orange')
        plt.xlabel('Simulation Step (Packet Index)')
        plt.ylabel('Number of PDUs in Buffer')
        plt.title('PDCP Receiver Reordering Buffer Occupancy')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        img_io = io.BytesIO()
        plt.savefig(img_io, format='png', bbox_inches='tight')
        img_io.seek(0)
        plots_base64['buffer_occupancy'] = base64.b64encode(img_io.getvalue()).decode('utf-8')
        plt.close()

    except Exception as e:
        app.logger.error(f"Error generating plot: {e}")
        # Optionally, return placeholder or error message for plots
    return plots_base64


@app.route('/')
def index():
    # Pass default config values to the template
    default_params = {
        'SN_LENGTH_BITS': default_config.SN_LENGTH_BITS,
        'SIMULATION_PACKETS': default_config.SIMULATION_PACKETS,
        'LOSS_RATE': default_config.LOSS_RATE,
        'REORDERING_RATE': default_config.REORDERING_RATE,
        'DUPLICATION_RATE': default_config.DUPLICATION_RATE,
        'CORRUPTION_RATE': default_config.CORRUPTION_RATE,
        'T_REORDERING_THRESHOLD': default_config.T_REORDERING_THRESHOLD,
    }
    return render_template('index.html', params=default_params)

@app.route('/run_simulation', methods=['POST'])
def handle_run_simulation():
    try:
        params_from_form = request.form
        app.logger.info(f"Received simulation request with params: {params_from_form}")

        sim_params = SimulationParameters(
            SN_LENGTH_BITS=int(params_from_form.get('sn_length_bits', default_config.SN_LENGTH_BITS)),
            SIMULATION_PACKETS=int(params_from_form.get('simulation_packets', default_config.SIMULATION_PACKETS)),
            LOSS_RATE=float(params_from_form.get('loss_rate', default_config.LOSS_RATE)),
            REORDERING_RATE=float(params_from_form.get('reordering_rate', default_config.REORDERING_RATE)),
            DUPLICATION_RATE=float(params_from_form.get('duplication_rate', default_config.DUPLICATION_RATE)),
            CORRUPTION_RATE=float(params_from_form.get('corruption_rate', default_config.CORRUPTION_RATE)),
            T_REORDERING_THRESHOLD=int(params_from_form.get('t_reordering_threshold', default_config.T_REORDERING_THRESHOLD)),
            PLOT_GRANULARITY=max(1, int(params_from_form.get('simulation_packets', default_config.SIMULATION_PACKETS)) // 200), # Dynamic granularity
            LOG_LEVEL=default_config.LOG_LEVEL # Keep log level from main config for now
        )
        
        # Ensure plot granularity is at least 1
        if sim_params.PLOT_GRANULARITY < 1:
            sim_params.PLOT_GRANULARITY = 1


        app.logger.info(f"Parsed Simulation Parameters: SN={sim_params.SN_LENGTH_BITS}, Packets={sim_params.SIMULATION_PACKETS}, Loss={sim_params.LOSS_RATE*100}%")
        
        results = run_simulation(sim_params) # run_simulation now takes a params object
        
        # Generate plots as base64 strings
        plot_images_base64 = {}
        if results.get("plot_data"):
            plot_images_base64 = generate_plots_base64(results["plot_data"])
        
        response_data = {
            "success": True,
            "metrics": {
                "total_sdu_sent": results["total_sdu_sent"],
                "tx_next_final": results["tx_status"]["tx_next_final"],
                "delivered_sdu_count": results["rx_status"]["delivered_sdu_count"],
                "rx_deliv_final": results["rx_status"]["rx_deliv"],
                "rx_next_final": results["rx_status"]["rx_next"],
                "buffered_final": results["rx_status"]["buffered_pdu_count"],
                "discarded_duplicates": results["rx_status"]["discarded_duplicates"],
                "discarded_old": results["rx_status"]["discarded_old"],
                "discarded_corrupted": results["rx_status"]["discarded_corrupted"],
                "out_of_order_deliveries": results["rx_status"]["out_of_order_deliveries"],
                "channel_lost": results["channel_stats"]["total_lost"],
                "channel_duplicated": results["channel_stats"]["total_duplicated"],
                "channel_corrupted": results["channel_stats"]["total_corrupted"],
                "channel_reorder_events": results["channel_stats"]["total_reordered_events"],
                "simulation_duration": f"{results['duration_seconds']:.2f}s"
            },
            "plots": plot_images_base64
        }
        return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"Error during simulation via web: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Create dummy plots and data folders if they don't exist, for main_cli compatibility
    if not os.path.exists("data"): os.makedirs("data")
    if not os.path.exists("plots"): os.makedirs("plots")
    app.run(debug=True) # debug=True for development