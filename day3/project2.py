import random
import matplotlib.pyplot as plt

# Define QFIs (for example: 5 for Voice, 9 for Video, 1 for Web Browsing)
QFIs = [5, 9, 1]
QFI_Labels = {
    5: 'Voice',
    9: 'Video',
    1: 'Web'
}

# Simulate number of packets to send
TOTAL_PACKETS = 200

# Simulate packet assignment to QFIs (randomly)
packet_distribution = {qfi: 0 for qfi in QFIs}

for _ in range(TOTAL_PACKETS):
    chosen_qfi = random.choices(QFIs, weights=[0.3, 0.5, 0.2])[0]  # Higher weight for QFI 9 (Video)
    packet_distribution[chosen_qfi] += 1

# Print results (console output)
print("Packet Count per QFI:", packet_distribution)

# Plotting the bar chart
plt.figure(figsize=(8, 5))
plt.bar(
    [f"QFI {qfi} ({QFI_Labels[qfi]})" for qfi in packet_distribution.keys()],
    list(packet_distribution.values()),
    color='skyblue',
    edgecolor='black'
)

plt.xlabel('QFI (Service Type)')
plt.ylabel('Number of Packets Sent')
plt.title('SDAP QoS Flow Packet Distribution')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()
