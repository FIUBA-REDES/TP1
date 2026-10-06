import os
import time
import logging
from queue import Queue, Empty
from .protocol import Packet

TIMEOUT = 5


class Session:
    """State and packet handling for one client transfer."""

    def __init__(self, transport, client_address, storage_dir=None, on_close=None):
        self.transport = transport
        self.client_address = client_address
        self.storage_dir = storage_dir
        self.on_close = on_close
        self.remote_name = None
        self.packets = Queue()
        self.chunks = {}
        self.buffer = bytearray()
        self.next_seq = 0
        self.completed = False
        self.file_bytes = b""
        self.fin_received = False
        self.fin_seq = None
        self.aborted = False

    def send_ack(self, packet):
        sack_payload = bytearray()

        for seq_num in sorted(self.chunks):
            sack_payload.extend(
                seq_num.to_bytes(4, byteorder="big")
            )

        ack_packet = Packet(
            Packet.OP_ACK,
            packet.seq_num,
            self.next_seq,
            bytes(sack_payload)
        )

        self.transport.send(ack_packet, self.client_address)

    def start_session(self, packet):
        self.remote_name = packet.payload.decode("utf-8")
        self.transport.send(
            Packet(
                Packet.OP_ACK,
                packet.seq_num,
                packet.seq_num,
                b""
            ),
            self.client_address
        )
    def enqueue(self, packet):
        self.packets.put(packet)

    def process_packets(self):
        try:
            while True:
                try:
                    packet = self.packets.get(timeout=TIMEOUT)
                except Empty:
                    self.aborted = True
                    return

                try:
                    if packet is None:
                        return

                    self.update_session(packet)

                    if self.completed:
                        return
                finally:
                    self.packets.task_done()
        finally:
            if self.on_close is not None:
                self.on_close(self)

    def update_session(self, packet):
        if packet.opcode == Packet.OP_DATA:
            if packet.seq_num >= self.next_seq:
                if packet.seq_num not in self.chunks:
                    self.chunks[packet.seq_num] = packet.payload

                while self.next_seq in self.chunks:
                    self.buffer.extend(self.chunks.pop(self.next_seq))
                    self.next_seq += 1

            self.send_ack(packet)

            if self.fin_received and self.next_seq == self.fin_seq:
                self.complete_transfer()

            return

        if packet.opcode == Packet.OP_FIN:
            logging.debug(f"FIN recibido: seq={packet.seq_num}")

            self.fin_received = True
            self.fin_seq = packet.seq_num

            self.send_ack(packet)

            if self.next_seq == self.fin_seq:
                self.complete_transfer()

            return

        if packet.opcode == Packet.OP_ERROR:
            logging.error(
                "Error del cliente: "
                + packet.payload.decode(
                    "utf-8",
                    errors="replace"
                )
            )

    def complete_transfer(self):
        self.completed = True
        self.file_bytes = bytes(self.buffer)

        if self.storage_dir is not None and self.remote_name:
            path = os.path.join(
                self.storage_dir,
                self.remote_name
            )

            with open(path, "wb") as file:
                file.write(self.file_bytes)

        logging.info(
            f"Transferencia completada: "
            f"{len(self.file_bytes)} bytes"
        )
