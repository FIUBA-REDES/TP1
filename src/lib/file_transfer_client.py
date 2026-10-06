import logging

from .protocol import Packet, handshake_start
from .transport import UdpTransport
from .stop_and_wait import MAX_TRIES, StopAndWait
from .sack import SelectiveRepeat


class FileTransferClient:

    def __init__(self, server_host, server_port, timeout=1.0):
        self.server_address = (server_host, server_port)
        self.transport = UdpTransport(timeout=timeout)
        self.connected = False

    def connect(self, remote_name=None):
        """Start a transfer session with the server."""
        payload = (
            b""
            if remote_name is None
            else remote_name.encode("utf-8")
        )

        start_packet = handshake_start(payload)

        for _ in range(MAX_TRIES):
            self.transport.send(
                start_packet,
                self.server_address
            )

            ack_packet, address = self.transport.receive()

            if (
                ack_packet is not None
                and address == self.server_address
                and ack_packet.opcode == Packet.OP_ACK
                and ack_packet.seq_num == start_packet.seq_num
            ):
                self.connected = True
                return True

            if (
                ack_packet is not None
                and address == self.server_address
                and ack_packet.opcode == Packet.OP_ERROR
            ):
                logging.error(
                    "Error del servidor: " +
                    ack_packet.payload.decode(
                        "utf-8",
                        errors="replace"
                    )  
                )
                self.connected = False
                return False

        logging.error("Error: no se recibió ACK del handshake.")
        self.connected = False
        return False

    def upload(self, source_path, remote_name=None, protocolo=None):
        """Upload a local file to the server."""

        if protocolo == "sw":
            if (StopAndWait.send(self.transport, source_path,
                                 self.server_address)) is False:
                logging.error("Error: Failed to send the file "
                      "using Stop-and-Wait protocol."
                )
                return
            else:
                logging.info(
                    f"File '{source_path}' sent successfully "
                    "using Stop-and-Wait protocol."
                )

        elif protocolo == "sack":
            if not SelectiveRepeat.send(
                    self.transport, source_path, self.server_address):
                logging.error("Error: Failed to send the file "
                      "using Selective Repeat protocol.")
                return
            else:
                logging.info(
                    f"File '{source_path}' sent successfully "
                    "using Selective Repeat protocol."
                    )
        else:
            raise ValueError(
                "Invalid protocol specified. Choose 'sw' or 'sack'.")

    def download(self, destination_path, remote_name=None, protocol=None):
        """Download a file from the server."""

        if protocol == "sw":
            if not self.connect("DOWNLOAD:sw:" + remote_name):
                return

            if StopAndWait.receive(self.transport, destination_path,
                                   self.server_address) is False:
                logging.error("Error: Failed to receive the file "
                      "using Stop-and-Wait protocol.")
                return
            else:
                logging.info(
                    f"File '{destination_path}' received successfully "
                    "using Stop-and-Wait protocol."
                    )

        elif protocol == "sack":
            if not self.connect("DOWNLOAD:sack:" + remote_name):
                return

            if not SelectiveRepeat.receive(
                    self.transport, destination_path, self.server_address):
                logging.error("Error: Failed to receive the file using "
                      "Selective Repeat protocol.")
                return
            else:
                logging.info(
                    f"File '{destination_path}' received successfully "
                    "using Selective Repeat protocol."
                    )
        else:
            raise ValueError(
                "Invalid protocol specified. Choose 'sw' or 'sack'.")

    def close(self):
        """Close the UDP transport."""
        self.transport.close()
        self.connected = False
