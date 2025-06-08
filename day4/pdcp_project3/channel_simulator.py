import random
from config import TAMPERING_RATE

class ChannelSimulator:
    def transmit(self, pdu):
        if random.random() < TAMPERING_RATE:
            pdu.is_corrupted = True
        return pdu