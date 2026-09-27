import unittest

from lib.file_transfer_server import FileTransferServer
from lib.protocol import Packet


class RecordingTransport:
    def __init__(self):
        self.acks = []

    def send(self, packet, address):
        self.acks.append((packet.seq_num, address))

    def close(self):
        pass


class ConcurrentSessionsTest(unittest.TestCase):
    def test_sessions_process_interleaved_packets_independently(self):
        server = FileTransferServer()
        server.transport.close()
        transport = RecordingTransport()
        server.transport = transport

        client_a = ("127.0.0.1", 41001)
        client_b = ("127.0.0.1", 41002)

        try:
            server.handle_packet(Packet(Packet.OP_START, 0, 0, b""), client_a)
            server.handle_packet(Packet(Packet.OP_START, 0, 0, b""), client_b)

            server.handle_packet(Packet(Packet.OP_DATA, 0, 0, b"A"), client_a)
            server.handle_packet(Packet(Packet.OP_DATA, 0, 0, b"B"), client_b)
            server.handle_packet(Packet(Packet.OP_FIN, 1, 0, b""), client_a)
            server.handle_packet(Packet(Packet.OP_FIN, 1, 0, b""), client_b)

            session_a = server.sessions[client_a]
            session_b = server.sessions[client_b]
            session_a.packets.join()
            session_b.packets.join()

            self.assertEqual(session_a.file_bytes, b"A")
            self.assertEqual(session_b.file_bytes, b"B")
            self.assertTrue(session_a.completed)
            self.assertTrue(session_b.completed)
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()