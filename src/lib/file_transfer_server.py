import os
from .protocol import Packet, ack
from .session import Session
from .transport import UdpTransport
from .stop_and_wait import StopAndWait
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


class FileTransferServer:
    """Server skeleton for receiving file transfer requests over UDP."""

    def __init__(self, host="127.0.0.1", port=5005, timeout=None, storage_dir="storage"):
        self.address = (host, port)
        self.transport = UdpTransport(timeout=timeout)
        self.sessions = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.lock = Lock()
        self.running = False
        self.storage_dir = storage_dir

    def start(self):
        """Bind the server socket and prepare the receive loop."""
        self.transport.bind(*self.address)
        self.running = True

    def serve_forever(self):
        """Receive packets and dispatch them while the server is running."""
        if not self.running:
            self.start()

        while self.running:
            packet, client_address = self.transport.receive()

            if packet is not None:
                self.handle_packet(packet, client_address)

    def handle_packet(self, packet, client_address):
        """Register a new client and dispatch its packet."""
        download_prefix = b"DOWNLOAD:"

        if (
            packet.opcode == Packet.OP_START
            and packet.payload.startswith(download_prefix)
        ):
            remote_name = packet.payload[len(download_prefix):].decode("utf-8")
            path = os.path.join(self.storage_dir, remote_name)

            if not os.path.isfile(path):
                error_packet = Packet(
                    Packet.OP_ERROR,
                    packet.seq_num,
                    0,
                    b"El archivo solicitado no existe."
                )
                self.transport.send(error_packet, client_address)
                return

            self.transport.send(ack(packet.seq_num), client_address)
            self.transport.set_timeout(1.0)
            try:
                StopAndWait.send(self.transport, path, client_address)
            finally:
                self.transport.set_timeout(None)
            return
        
        with self.lock:
            client_session = self.sessions.get(client_address)

            if packet.opcode == Packet.OP_START:
                if client_session is None:
                    client_session = Session(
                        self.transport,
                        client_address,
                        self.storage_dir,
                    )
                    self.sessions[client_address] = client_session
                    self.executor.submit(client_session.process_packets)

                client_session.start_session(packet)
                return

            if client_session is not None:
                client_session.enqueue(packet)

    def stop(self):
        """Stop receiving packets and close the UDP transport."""
        self.running = False
        with self.lock:
            for client_session in self.sessions.values():
                client_session.enqueue(None)
        self.executor.shutdown(wait=True)
        self.transport.close()
