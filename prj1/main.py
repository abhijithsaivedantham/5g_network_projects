import logging
import time
import json
import os
from datetime import datetime

from src.pdcp_entity import PDCPTransmitter, PDCPReceiver
from src.channel_simulator import ImpairedChannel
from src.pdcp_packet import PDCP_PDU # For type hinting if needed
import config # Simulation parameters from config.py

# --- Initialize module-level logger ---
# This logger will be used by functions within this main.py file.
# The src/ modules will create their own loggers which will also benefit from basicConfig.
logger = logging.getLogger(__name__)

# --- Data Collection for Plotting (Global within this module) ---
tx_counts_log = []
rx_deliv_log = []
rx_next_log = []
reordering_buffer_size_log = []
simulation_time_log = [] # Relative time or packet number

def setup_logging(log_level_str):
    level = getattr(logging, log_level_str.upper(), logging.INFO)
    # Configure the root logger. All other loggers will inherit this configuration
    # unless they have specific handlers or propagation settings.
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info(f"Logging initialized at level {log_level_str.upper()} for the application.")

def run_simulation(params):
    """
    Runs a single simulation with given parameters.
    `params` is a dictionary-like object (e.g., config module or a dict).
    """
    # Note: setup_logging() is now called in main_cli() or at the start of the script if run directly.
    # The module-level 'logger' is used throughout this function.

    # Clear previous log data
    tx_counts_log.clear()
    rx_deliv_log.clear()
    rx_next_log.clear()
    reordering_buffer_size_log.clear()
    simulation_time_log.clear()

    # Initialize PDCP entities and Channel
    transmitter = PDCPTransmitter(sn_length=params.SN_LENGTH_BITS)
    receiver = PDCPReceiver(sn_length=params.SN_LENGTH_BITS,
                            t_reordering_threshold=params.T_REORDERING_THRESHOLD)
    channel = ImpairedChannel(
        loss_rate=params.LOSS_RATE,
        reordering_rate=params.REORDERING_RATE,
        duplication_rate=params.DUPLICATION_RATE,
        corruption_rate=params.CORRUPTION_RATE,
    )

    logger.info("Starting PDCP Simulation...") # Uses module-level logger
    start_time = time.time()

    total_sdu_to_send = params.SIMULATION_PACKETS
    for i in range(total_sdu_to_send):
        sdu_payload = f"SDU_data_{i}"
        pdcp_pdu = transmitter.send_sdu(sdu_id=i, sdu_payload=sdu_payload)
        pdus_from_channel = channel.transmit([pdcp_pdu])
        for p_out_ch in pdus_from_channel:
            receiver.receive_pdu(p_out_ch)

        if i % getattr(params, "PLOT_GRANULARITY", 1) == 0 or i == total_sdu_to_send - 1:
            tx_counts_log.append(transmitter.tx_next)
            rx_deliv_log.append(receiver.rx_deliv)
            rx_next_log.append(receiver.rx_next)
            reordering_buffer_size_log.append(len(receiver.reordering_buffer))
            simulation_time_log.append(i)

    receiver.flush_buffer()
    end_time = time.time()
    simulation_duration = end_time - start_time
    logger.info(f"Simulation finished in {simulation_duration:.2f} seconds.")

    tx_status = {"tx_next_final": transmitter.tx_next}
    rx_status = receiver.get_status()
    channel_stats = channel.get_stats()
    lost_sdu_count = total_sdu_to_send - rx_status["delivered_sdu_count"]

    logger.info("--- Simulation Summary ---")
    logger.info(f"Total SDUs Sent: {total_sdu_to_send}")
    logger.info(f"Transmitter Next COUNT: {tx_status['tx_next_final']}")
    logger.info(f"Receiver Delivered SDUs: {rx_status['delivered_sdu_count']}")
    logger.info(f"Receiver RX_DELIV: {rx_status['rx_deliv']}")
    logger.info(f"Receiver RX_NEXT: {rx_status['rx_next']}")
    logger.info(f"Receiver Buffered PDUs at End: {rx_status['buffered_pdu_count']}")
    logger.info(f"Receiver Discarded (Duplicate): {rx_status['discarded_duplicates']}")
    logger.info(f"Receiver Discarded (Old): {rx_status['discarded_old']}")
    logger.info(f"Receiver Discarded (Corrupted): {rx_status['discarded_corrupted']}")
    logger.info(f"Receiver Out-of-Order Deliveries (t-Reordering): {rx_status['out_of_order_deliveries']}")
    logger.info(f"Channel Stats: {channel_stats}")
    logger.info(f"Calculated Lost/Undelivered SDUs: {lost_sdu_count}")

    results = {
        "simulation_parameters": {k: v for k, v in vars(params).items() if not k.startswith('_') and isinstance(v, (int, float, str, bool))},
        "duration_seconds": simulation_duration,
        "total_sdu_sent": total_sdu_to_send,
        "tx_status": tx_status,
        "rx_status": rx_status,
        "channel_stats": channel_stats,
        "calculated_lost_sdu": lost_sdu_count,
        "plot_data": {
            "time": simulation_time_log,
            "tx_count": tx_counts_log,
            "rx_deliv": rx_deliv_log,
            "rx_next": rx_next_log,
            "buffer_size": reordering_buffer_size_log
        }
    }
    return results

def save_results(results, base_filename="sim_results"):
    if not os.path.exists("data"):
        os.makedirs("data")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join("data", f"{base_filename}_{timestamp}.json")
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=4)
    logger.info(f"Simulation results saved to {filepath}") # Uses module-level logger
    return filepath

def main_cli():
    # Setup logging ONCE at the beginning of the script execution for CLI mode.
    # For the web app (app.py), Flask's own logger or a similar setup in app.py handles logging.
    setup_logging(config.LOG_LEVEL)

    results = run_simulation(config)
    results_filepath = save_results(results)

    if config.ENABLE_PLOTTING:
        try:
            import matplotlib.pyplot as plt
            if not os.path.exists("plots"):
                os.makedirs("plots")
            
            plot_data = results["plot_data"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            plt.figure(figsize=(12, 6))
            plt.plot(plot_data["time"], plot_data["tx_count"], label='TX_NEXT (Transmitter COUNT)', linestyle='--')
            plt.plot(plot_data["time"], plot_data["rx_deliv"], label='RX_DELIV (Receiver In-Sequence Delivered)')
            plt.plot(plot_data["time"], plot_data["rx_next"], label='RX_NEXT (Receiver Highest Seen+1)', linestyle=':')
            plt.xlabel('Simulation Step (Packet Index)')
            plt.ylabel('COUNT Value')
            plt.title('PDCP COUNT Progression')
            plt.legend()
            plt.grid(True)
            plot_path1 = os.path.join("plots", f"count_progression_{timestamp}.png")
            plt.savefig(plot_path1)
            plt.close()
            logger.info(f"COUNT progression plot saved to {plot_path1}") # Uses module-level logger

            plt.figure(figsize=(12, 6))
            plt.plot(plot_data["time"], plot_data["buffer_size"], label='Receiver Reordering Buffer Size')
            plt.xlabel('Simulation Step (Packet Index)')
            plt.ylabel('Number of PDUs in Buffer')
            plt.title('PDCP Receiver Reordering Buffer Occupancy')
            plt.legend()
            plt.grid(True)
            plot_path2 = os.path.join("plots", f"buffer_occupancy_{timestamp}.png")
            plt.savefig(plot_path2)
            plt.close()
            logger.info(f"Buffer occupancy plot saved to {plot_path2}") # Uses module-level logger

        except ImportError:
            logger.warning("Matplotlib not installed. Skipping plot generation. Please install with: pip install matplotlib") # Uses module-level logger
        except Exception as e:
            logger.error(f"Error during plotting: {e}") # Uses module-level logger

if __name__ == "__main__":
    main_cli()