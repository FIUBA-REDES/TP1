from .protocol import Packet
from .transport import UdpTransport


class FileTransferServer:
    """Server skeleton for receiving file transfer requests over UDP."""

    def __init__(self, host="127.0.0.1", port=5005, timeout=None):
        self.address = (host, port)
        self.transport = UdpTransport(timeout=timeout)
        self.sessions = {}
        self.running = False

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
            self.handle_packet(packet, client_address)

    def handle_packet(self, packet, client_address):
        """Register a new client and dispatch its packet."""
        if packet.opcode == Packet.OP_START:
            self.sessions[client_address] = packet

    def stop(self):
        """Stop receiving packets and close the UDP transport."""
        self.running = False
        self.transport.close()
