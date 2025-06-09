import asyncio
import random
import time
from collections import deque
import json

class RLC_PDU:
    def __init__(self, seq_num, data, size):
        self.seq_num = seq_num
        self.data = data
        self.size = size
        self.acked = False
        self.sent_time = None

class RLCEntity:
    def __init__(self, mode, buffer_size=1000, reordering_timer=0.1, poll_timer=0.05):
        self.mode = mode  # 'AM' or 'UM'
        self.buffer_size = buffer_size
        self.tx_buffer = deque(maxlen=buffer_size)
        self.rx_buffer = deque()
        self.next_seq_num = 0
        self.reordering_timer = reordering_timer
        self.poll_timer = poll_timer
        self.acked_seq = -1
        self.stats = {
            'sent_pdus': 0,
            'received_pdus': 0,
            'retransmissions': 0,
            'packet_loss': 0,
            'total_latency': 0,
            'buffer_occupancy': 0,
            'throughput': 0
        }

    def send_pdu(self, data, size, packet_loss_prob):
        pdu = RLC_PDU(self.next_seq_num, data, size)
        pdu.sent_time = time.time()
        self.tx_buffer.append(pdu)
        self.stats['sent_pdus'] += 1
        self.stats['buffer_occupancy'] = len(self.tx_buffer)
        self.next_seq_num += 1
        if random.random() > packet_loss_prob:
            return pdu
        self.stats['packet_loss'] += 1
        return None

    async def receive_pdu(self, pdu, packet_loss_prob):
        if pdu is None:
            return
        if self.mode == 'AM':
            if random.random() > packet_loss_prob:
                self.rx_buffer.append(pdu)
                self.stats['received_pdus'] += 1
                latency = time.time() - pdu.sent_time
                self.stats['total_latency'] += latency
                pdu.acked = True
                self.acked_seq = max(self.acked_seq, pdu.seq_num)
        else:  # UM
            self.rx_buffer.append(pdu)
            self.stats['received_pdus'] += 1
            latency = time.time() - pdu.sent_time
            self.stats['total_latency'] += latency

    async def retransmit(self, packet_loss_prob):
        if self.mode != 'AM':
            return
        for pdu in list(self.tx_buffer):
            if not pdu.acked and (time.time() - pdu.sent_time) > self.reordering_timer:
                self.stats['retransmissions'] += 1
                if random.random() > packet_loss_prob:
                    self.rx_buffer.append(pdu)
                    self.stats['received_pdus'] += 1
                    latency = time.time() - pdu.sent_time
                    self.stats['total_latency'] += latency
                    pdu.acked = True
                    self.acked_seq = max(self.acked_seq, pdu.seq_num)

    def segment_sdu(self, sdu_data, max_pdu_size):
        pdus = []
        for i in range(0, len(sdu_data), max_pdu_size):
            pdu_data = sdu_data[i:i + max_pdu_size]
            pdus.append(RLC_PDU(self.next_seq_num, pdu_data, len(pdu_data)))
            self.next_seq_num += 1
        return pdus

    def compute_kpis(self, duration):
        retrans_rate = self.stats['retransmissions'] / max(self.stats['sent_pdus'], 1)
        throughput = self.stats['received_pdus'] / max(duration, 1)
        avg_latency = self.stats['total_latency'] / max(self.stats['received_pdus'], 1) if self.stats['received_pdus'] > 0 else 0
        packet_loss_rate = self.stats['packet_loss'] / max(self.stats['sent_pdus'], 1)
        buffer_occ = self.stats['buffer_occupancy'] / self.buffer_size
        return {
            'retransmission_rate': retrans_rate,
            'throughput': throughput,
            'avg_latency': avg_latency,
            'packet_loss_rate': packet_loss_rate,
            'buffer_occupancy': buffer_occ
        }

async def run_test_scenario(mode, scenario, num_pdus=100, packet_loss_prob=0.0, large_sdu=False, buffer_overflow=False):
    rlc = RLCEntity(mode=mode, buffer_size=50 if buffer_overflow else 1000)
    start_time = time.time()
    results = {'mode': mode, 'scenario': scenario, 'logs': []}
    
    if large_sdu:
        sdu = "A" * 1000
        pdus = rlc.segment_sdu(sdu, 100)
        for pdu in pdus:
            sent_pdu = rlc.send_pdu(pdu.data, pdu.size, packet_loss_prob)
            await rlc.receive_pdu(sent_pdu, packet_loss_prob)
            await asyncio.sleep(0.01)
    else:
        for _ in range(num_pdus):
            data = "TestData"
            size = len(data)
            sent_pdu = rlc.send_pdu(data, size, packet_loss_prob)
            await rlc.receive_pdu(sent_pdu, packet_loss_prob)
            await rlc.retransmit(packet_loss_prob)
            await asyncio.sleep(0.01)
    
    duration = time.time() - start_time
    kpis = rlc.compute_kpis(duration)
    results['kpis'] = kpis
    results['logs'].append(f"Sent: {rlc.stats['sent_pdus']}, Received: {rlc.stats['received_pdus']}, Retrans: {rlc.stats['retransmissions']}")
    return results

async def run_all_tests():
    tests = [
        ('AM', 'Baseline (No Loss)', 100, 0.0, False, False),
        ('AM', 'Moderate Loss (10%)', 100, 0.1, False, False),
        ('AM', 'High Loss (30%)', 100, 0.3, False, False),
        ('AM', 'Buffer Overflow', 200, 0.0, False, True),
        ('UM', 'Real-Time Video', 100, 0.0, False, False),
        ('UM', 'Lossy Environment (15%)', 100, 0.15, False, False),
        ('UM', 'Segmentation', 10, 0.0, True, False)
    ]
    results = []
    for mode, scenario, num_pdus, loss_prob, large_sdu, buffer_overflow in tests:
        result = await run_test_scenario(mode, scenario, num_pdus, loss_prob, large_sdu, buffer_overflow)
        results.append(result)
    return results

async def main():
    results = await run_all_tests()
    return json.dumps(results, indent=2)

if __name__ == "__main__":
    results = asyncio.run(main())
    print(results)