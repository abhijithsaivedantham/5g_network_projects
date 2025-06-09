import random
import time

# --- Configuration ---
NUM_HARQ_PROCESSES = 8
MAX_RETRANSMISSIONS = 3  # Initial Tx + 3 retransmissions
RV_SEQUENCE = [0, 2, 3, 1]

class HarqProcess:
    """Represents a single HARQ process state."""
    def __init__(self, process_id):
        self.id = process_id
        # gNB state
        self.busy = False
        self.ndi = 0
        self.rv_index = 0
        self.data = None
        self.tx_count = 0
        # UE state
        self.ue_last_ndi = 0
        self.ue_soft_buffer = 0

    def __str__(self):
        status = "Busy" if self.busy else "Idle"
        return (f"ID: {self.id} | Status: {status} | NDI: {self.ndi} | "
                f"RV: {RV_SEQUENCE[self.rv_index]} | Data: {self.data} | Tx: {self.tx_count} | "
                f"UE Buffer: {self.ue_soft_buffer}")

class HarqEntity:
    """Manages all HARQ processes for gNB or UE."""
    def __init__(self):
        self.processes = [HarqProcess(i) for i in range(NUM_HARQ_PROCESSES)]

    def print_state(self, entity_name):
        print(f"\n--- {entity_name} State ---")
        for p in self.processes:
            print(p)
        print("-" * (len(entity_name) + 12))

# --- Simulation Logic ---
def simulate_ue_decoding(process):
    """Simulates the UE's attempt to decode a packet."""
    # Success chance increases with each retransmission (more soft-bits)
    success_chance = 0.3 + process.ue_soft_buffer * 0.35
    if random.random() < success_chance:
        return "ACK"
    else:
        return "NACK"

def run_simulation(steps):
    entity = HarqEntity()
    packet_counter = 0

    for step in range(steps):
        print(f"\n\n======= Simulation Step {step + 1} =======")
        entity.print_state("Start of Step")
        
        # 1. Prioritize Retransmissions
        process_to_retransmit = None
        for p in entity.processes:
            if p.busy and 0 < p.tx_count <= MAX_RETRANSMISSIONS:
                process_to_retransmit = p
                break
        
        if process_to_retransmit:
            p = process_to_retransmit
            print(f"\n[ACTION] Retransmitting for Process {p.id}")
            p.rv_index = (p.rv_index + 1) % len(RV_SEQUENCE)
            p.tx_count += 1
            print(f"         gNB: Sending packet '{p.data}' (NDI={p.ndi}, RV={RV_SEQUENCE[p.rv_index]})")
        
        # 2. If no retransmissions, start a new transmission
        else:
            idle_process = None
            for p in entity.processes:
                if not p.busy:
                    idle_process = p
                    break
            
            if idle_process:
                p = idle_process
                print(f"\n[ACTION] New transmission on Process {p.id}")
                packet_counter += 1
                p.data = f"Pkt_{packet_counter}"
                p.ndi = 1 - p.ndi  # Toggle NDI
                p.rv_index = 0
                p.tx_count = 1
                p.busy = True
                print(f"         gNB: Sending packet '{p.data}' (NDI={p.ndi}, RV={RV_SEQUENCE[p.rv_index]})")
            else:
                print("\n[INFO] All HARQ processes are busy. Waiting for ACKs.")
                time.sleep(1)
                continue

        # 3. UE receives and provides feedback
        p = process_to_retransmit or idle_process
        if p.ndi != p.ue_last_ndi:
            print(f"         UE: NDI toggled on Process {p.id}. Clearing soft buffer.")
            p.ue_last_ndi = p.ndi
            p.ue_soft_buffer = 0

        feedback = simulate_ue_decoding(p)
        print(f"         UE: Decoding attempt... Result: {feedback}")

        # 4. gNB processes feedback
        if feedback == "ACK":
            print(f"         gNB: Received ACK for Process {p.id}. Process is now free.")
            p.busy = False
            p.data = None
            p.tx_count = 0
            p.ue_soft_buffer = 0
        else: # NACK
            p.ue_soft_buffer += 1
            if p.tx_count > MAX_RETRANSMISSIONS:
                print(f"         gNB: Received NACK, but max retransmissions reached for Process {p.id}. Packet discarded.")
                p.busy = False
                p.data = None
                p.tx_count = 0
                p.ue_soft_buffer = 0
            else:
                print(f"         gNB: Received NACK for Process {p.id}. Will retransmit on a future step.")
        
        entity.print_state("End of Step")
        time.sleep(1)

if __name__ == "__main__":
    run_simulation(steps=20)