# Simulation Parameters
SN_LENGTH_BITS = 12  # Can be 12 or 18
SIMULATION_PACKETS = 1000  # Number of SDUs to send
# SIMULATION_PACKETS = 5000 # For wrap-around testing with 12-bit SN

# Channel Impairment Rates
LOSS_RATE = 0.01          # Packet loss rate (0.0 to 1.0)
REORDERING_RATE = 0.02    # Packet reordering rate (0.0 to 1.0)
DUPLICATION_RATE = 0.01   # Packet duplication rate (0.0 to 1.0)
CORRUPTION_RATE = 0.005   # Packet corruption rate (0.0 to 1.0)

# PDCP Receiver Parameters
# Window_Size for HFN calculation is 2**(SN_LENGTH_BITS - 1) as per spec, calculated in PDCPReceiver
T_REORDERING_THRESHOLD = 20  # Number of PDUs received while timer is active to trigger expiry
                               # Or, if a gap persists for this many subsequently processed PDUs.

# Channel Simulator Parameters
CHANNEL_REORDER_BUFFER_SIZE = 10 # Max packets channel holds for potential reordering

# Plotting
ENABLE_PLOTTING = True
PLOT_GRANULARITY = 50 # Plot data points every N packets for large simulations to keep plots readable

# Logging
LOG_LEVEL = "INFO" # DEBUG, INFO, WARNING, ERROR