# 5G NR PDCP Sequence Numbering Simulation and Robustness Testing

## Project Goal
To design, implement, and test a Python-based simulation environment that accurately models the PDCP layer's sequence numbering (SN), Hyper Frame Number (HFN), and combined COUNT value management for both transmitting and receiving entities in 5G New Radio (NR). The project focuses on verifying the robustness and correctness of the HFN estimation logic and overall sequence integrity under various channel impairments (packet loss, reordering, duplication, and SN wrap-around scenarios).

## Core Concepts Implemented & Tested
- PDCP Sequence Number (PDCP SN): 12-bit or 18-bit.
- Hyper Frame Number (HFN): Maintained by transmitter and receiver.
- COUNT: Full 32-bit sequence number ([HFN | PDCP SN]).
- Transmitter Logic (TX_NEXT).
- Receiver Logic (RX_DELIV, RX_NEXT, RX_REORD, Window_Size for HFN estimation).
- PDCP Reordering Buffer.
- Simplified t-Reordering timer mechanism.
- Channel Impairments: Packet loss, reordering, duplication, corruption.

## Project Structure