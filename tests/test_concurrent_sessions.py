from lib.file_transfer_server import FileTransferServer
from lib.protocol import Packet


class RecordingTransport:
    def __init__(self):
        self.acks = []

    def send(self, packet, address):
        self.acks.append((packet.seq_num, address))

    def close(self):
        pass


def wait_for_sessions(server, clients):
    for client in clients:
        server.sessions[client].packets.join()


def test_two_sessions_process_interleaved_packets_independently():
    server = FileTransferServer()
    server.transport.close()
    server.transport = RecordingTransport()

    client_a = ("127.0.0.1", 41001)
    client_b = ("127.0.0.1", 41002)

    try:
        server.handle_packet(
            Packet(Packet.OP_START, 0, 0, b""),
            client_a,
        )
        server.handle_packet(
            Packet(Packet.OP_START, 0, 0, b""),
            client_b,
        )

        server.handle_packet(
            Packet(Packet.OP_DATA, 0, 0, b"A"),
            client_a,
        )
        server.handle_packet(
            Packet(Packet.OP_DATA, 0, 0, b"B"),
            client_b,
        )
        server.handle_packet(
            Packet(Packet.OP_FIN, 1, 0, b""),
            client_a,
        )
        server.handle_packet(
            Packet(Packet.OP_FIN, 1, 0, b""),
            client_b,
        )

        wait_for_sessions(server, [client_a, client_b])

        session_a = server.sessions[client_a]
        session_b = server.sessions[client_b]

        assert session_a.file_bytes == b"A"
        assert session_b.file_bytes == b"B"
        assert session_a.completed is True
        assert session_b.completed is True

    finally:
        server.stop()


def test_three_sessions_remain_independent():
    server = FileTransferServer()
    server.transport.close()
    server.transport = RecordingTransport()

    clients = [
        ("127.0.0.1", 42001),
        ("127.0.0.1", 42002),
        ("127.0.0.1", 42003),
    ]

    data = {
        clients[0]: b"AAA",
        clients[1]: b"BBB",
        clients[2]: b"CCC",
    }

    try:
        for client in clients:
            server.handle_packet(
                Packet(Packet.OP_START, 0, 0, b""),
                client,
            )

        for client in clients:
            server.handle_packet(
                Packet(Packet.OP_DATA, 0, 0, data[client]),
                client,
            )

        for client in clients:
            server.handle_packet(
                Packet(Packet.OP_FIN, 1, 0, b""),
                client,
            )

        wait_for_sessions(server, clients)

        for client in clients:
            session = server.sessions[client]
            assert session.file_bytes == data[client]
            assert session.completed is True

    finally:
        server.stop()


def test_sessions_do_not_mix_their_data():
    server = FileTransferServer()
    server.transport.close()
    server.transport = RecordingTransport()

    client_a = ("127.0.0.1", 43001)
    client_b = ("127.0.0.1", 43002)

    try:
        server.handle_packet(
            Packet(Packet.OP_START, 0, 0, b""),
            client_a,
        )
        server.handle_packet(
            Packet(Packet.OP_START, 0, 0, b""),
            client_b,
        )

        server.handle_packet(
            Packet(Packet.OP_DATA, 0, 0, b"Hola "),
            client_a,
        )
        server.handle_packet(
            Packet(Packet.OP_DATA, 0, 0, b"Chau "),
            client_b,
        )
        server.handle_packet(
            Packet(Packet.OP_DATA, 1, 0, b"A"),
            client_a,
        )
        server.handle_packet(
            Packet(Packet.OP_DATA, 1, 0, b"B"),
            client_b,
        )

        server.handle_packet(
            Packet(Packet.OP_FIN, 2, 0, b""),
            client_a,
        )
        server.handle_packet(
            Packet(Packet.OP_FIN, 2, 0, b""),
            client_b,
        )

        wait_for_sessions(server, [client_a, client_b])

        session_a = server.sessions[client_a]
        session_b = server.sessions[client_b]

        assert session_a.file_bytes == b"Hola A"
        assert session_b.file_bytes == b"Chau B"
        assert session_a.file_bytes != session_b.file_bytes

    finally:
        server.stop()
