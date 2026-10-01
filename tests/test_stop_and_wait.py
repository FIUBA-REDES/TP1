import threading
from lib.transport import UdpTransport
from lib.protocol import Packet
from lib.stop_and_wait import StopAndWait, MAX_TRIES

def test_receive(tmp_path):
    server = UdpTransport("127.0.0.1", 6250)
    client = UdpTransport("127.0.0.1", 6251, timeout=0.5)

    destination = tmp_path / "received.txt"
    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(server, destination, ("127.0.0.1", 6251))

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 6250)

    try:
        packets = [
            Packet(Packet.OP_DATA, 0, 0, b"Hola "),
            Packet(Packet.OP_DATA, 1, 0, b"mundo"),
            Packet(Packet.OP_FIN, 2, 0, b"")
        ]

        for packet in packets:
            client.send(packet, server_address)

            ack, address = client.receive()

            assert ack is not None
            assert address == server_address
            assert ack.opcode == Packet.OP_ACK
            assert ack.seq_num == packet.seq_num

        thread.join(timeout=2)

        assert not thread.is_alive()
        assert result["data"] is True
        assert destination.read_bytes() == b"Hola mundo"
    
    finally:
        client.close()
        server.close()

def test_receive_duplicate(tmp_path):
    server = UdpTransport("127.0.0.1", 7000)
    client = UdpTransport("127.0.0.1", 7001, timeout=0.5)

    destination = tmp_path / "received.txt"
    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(server, destination, ("127.0.0.1", 7001))

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 7000)

    try:
        packets = [
            Packet(Packet.OP_DATA, 0, 0, b"Hola "),
            Packet(Packet.OP_DATA, 1, 0, b"mundo"),
            Packet(Packet.OP_DATA, 1, 0, b"mundo"),
            Packet(Packet.OP_FIN, 2, 0, b""),
        ]

        for packet in packets:
            client.send(packet, server_address)

            ack, address = client.receive()

            assert ack is not None
            assert address == server_address
            assert ack.opcode == Packet.OP_ACK
            assert ack.seq_num == packet.seq_num

        thread.join(timeout=2)

        assert not thread.is_alive()
        assert result["data"] is True
        assert destination.read_bytes() == b"Hola mundo"

    finally:
        client.close()
        server.close()

def test_send_and_receive(tmp_path):
    server = UdpTransport("127.0.0.1", 7100)
    client = UdpTransport("127.0.0.1", 7101, timeout=0.5)

    file_path = tmp_path / "test.txt"
    destination = tmp_path / "received.txt"
    file_path.write_bytes(b"Hola mundo desde Stop and Wait")

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(server, destination, ("127.0.0.1", 7101))

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 7100)

    try:
        send_result = StopAndWait.send(client,file_path,server_address)

        thread.join(timeout=3)

        assert send_result is True
        assert not thread.is_alive()
        assert result["data"] is True
        assert destination.read_bytes() == file_path.read_bytes()

    finally:
        client.close()
        server.close()

class DropFirstAckTransport(UdpTransport):

    def __init__(self, host, port, timeout=0.5):
        super().__init__(host, port, timeout=timeout)
        self.drop_ack = True

    def send(self, packet, address):
        if packet.opcode == Packet.OP_ACK and self.drop_ack:
            self.drop_ack = False
            return len(packet.encode())

        return super().send(packet, address)


def test_send_and_receive_lost_ack(tmp_path):
    server = DropFirstAckTransport("127.0.0.1", 7200)
    client = UdpTransport("127.0.0.1", 7201, timeout=0.2)

    file_path = tmp_path / "test.txt"
    destination = tmp_path / "received.txt"
    file_path.write_bytes(b"Hola mundo desde Stop and Wait")

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(server, destination, ("127.0.0.1", 7201))

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 7200)
    try:
        send_result = StopAndWait.send(client, file_path, server_address)

        thread.join(timeout=3)

        assert send_result is True
        assert not thread.is_alive()
        assert result["data"] is True
        assert destination.read_bytes() == file_path.read_bytes()

    finally:
        client.close()
        server.close()

def test_send_empty_file(tmp_path):
    server = UdpTransport("127.0.0.1", 7300)
    client = UdpTransport("127.0.0.1", 7301, timeout=0.2)

    file_path = tmp_path / "empty.bin"
    destination = tmp_path / "received.bin"
    file_path.write_bytes(b"")

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(
            server,
            destination,
            ("127.0.0.1", 7301),
        )

    thread = threading.Thread(target=server_receive)
    thread.start()

    try:
        send_result = StopAndWait.send(
            client,
            file_path,
            ("127.0.0.1", 7300),
        )

        thread.join(timeout=3)

        assert send_result is True
        assert not thread.is_alive()
        assert result["data"] is True
        assert destination.read_bytes() == b""
    finally:
        client.close()
        server.close()


def test_send_binary_file(tmp_path):
    server = UdpTransport("127.0.0.1", 7400)
    client = UdpTransport("127.0.0.1", 7401, timeout=0.5)

    original = bytes(range(256)) * 20
    file_path = tmp_path / "binary.bin"
    destination = tmp_path / "received.bin"
    file_path.write_bytes(original)

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(
            server,
            destination,
            ("127.0.0.1", 7401),
        )

    thread = threading.Thread(target=server_receive)
    thread.start()

    try:
        send_result = StopAndWait.send(
            client,
            file_path,
            ("127.0.0.1", 7400),
        )

        thread.join(timeout=3)

        assert send_result is True
        assert not thread.is_alive()
        assert result["data"] is True
        assert destination.read_bytes() == original
    finally:
        client.close()
        server.close()


class WrongFirstAckTransport(UdpTransport):
    def __init__(self, host, port, timeout=0.2):
        super().__init__(host, port, timeout=timeout)
        self.wrong_ack_sent = False

    def receive(self, buffer_size=65535):
        packet, address = super().receive(buffer_size)

        if packet is not None and not self.wrong_ack_sent:
            self.wrong_ack_sent = True
            wrong_ack = Packet(
                Packet.OP_ACK,
                packet.seq_num + 100,
                0,
                b"",
            )
            return wrong_ack, address

        return packet, address


def test_send_ignores_wrong_ack(tmp_path):
    server = UdpTransport("127.0.0.1", 7500)
    client = WrongFirstAckTransport("127.0.0.1", 7501)

    file_path = tmp_path / "test.txt"
    destination = tmp_path / "received.txt"
    file_path.write_bytes(b"ACK incorrecto")

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(
            server,
            destination,
            ("127.0.0.1", 7501),
        )

    thread = threading.Thread(target=server_receive)
    thread.start()

    try:
        send_result = StopAndWait.send(
            client,
            file_path,
            ("127.0.0.1", 7500),
        )

        thread.join(timeout=3)

        assert send_result is True
        assert not thread.is_alive()
        assert result["data"] is True
        assert destination.read_bytes() == b"ACK incorrecto"
    finally:
        client.close()
        server.close()


class NoAckTransport:
    def __init__(self):
        self.send_count = 0

    def send(self, packet, address):
        self.send_count += 1
        return len(packet.encode())

    def receive(self, buffer_size=65535):
        return None, None


def test_send_stops_after_max_retries(tmp_path):
    transport = NoAckTransport()
    file_path = tmp_path / "empty.bin"
    file_path.write_bytes(b"")

    result = StopAndWait.send(
        transport,
        file_path,
        ("127.0.0.1", 7600),
    )

    assert result is False
    assert transport.send_count == MAX_TRIES