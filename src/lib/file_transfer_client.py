from .protocol import handshake_start
from .transport import UdpTransport


class FileTransferClient:
    """Client skeleton for uploading and downloading files over UDP."""

    def __init__(self, server_host, server_port, timeout=1.0):
        self.server_address = (server_host, server_port)
        self.transport = UdpTransport(timeout=timeout)
        self.connected = False

    def connect(self):
        """Start a transfer session with the server."""
        self.transport.send(handshake_start(), self.server_address)
        self.connected = True

    def upload(self, source_path, remote_name=None, protocolo=None):
        """Upload a local file to the server."""
        raise NotImplementedError

    def download(self, destination_path, remote_name=None, protocol=None):
        """Download a file from the server."""
        raise NotImplementedError

    def close(self):
        """Close the UDP transport."""
        self.transport.close()
        self.connected = False
