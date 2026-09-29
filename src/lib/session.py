import os
from queue import Queue
from sys import path
from .protocol import Packet, ack


class Session:
    """State and packet handling for one client transfer."""

    def __init__(self, transport, client_address, storage_dir=None):
        self.transport = transport
        self.client_address = client_address
        self.storage_dir = storage_dir
        self.remote_name = None
        self.packets = Queue()
        self.chunks = {}
        self.buffer = bytearray()
        self.next_seq = 0
        self.completed = False
        self.file_bytes = b""

    def send_ack(self, seq_num):
        self.transport.send(ack(seq_num), self.client_address)

    def start_session(self, packet):
        self.remote_name = packet.payload.decode("utf-8")
        self.send_ack(packet.seq_num)

    def enqueue(self, packet):
        self.packets.put(packet)

    def process_packets(self):
        while True:
            packet = self.packets.get()
            try:
                if packet is None:
                    return

                self.update_session(packet)
                if self.completed:
                    return
            finally:
                self.packets.task_done()

    def update_session(self, packet):
        if packet.opcode == Packet.OP_DATA:
            #Si el paquete recibido tiene un número de secuencia mayor que el siguiente esperado, se almacena en el diccionario de chunks
            if packet.seq_num not in self.chunks:
                self.chunks[packet.seq_num] = packet.payload

            while self.next_seq in self.chunks:
                self.buffer.extend(self.chunks.pop(self.next_seq))
                self.next_seq += 1

            self.send_ack(packet.seq_num)
            return False

        if packet.opcode == Packet.OP_FIN:
            self.completed = not self.chunks

            if self.completed:
                self.file_bytes = bytes(self.buffer)

                if self.storage_dir is not None and self.remote_name:
                    path = os.path.join(
                        self.storage_dir,
                        self.remote_name
                    )

                    with open(path, "wb") as file:
                        file.write(self.file_bytes)

            self.send_ack(packet.seq_num)
            return self.completed

        return False


session = Session