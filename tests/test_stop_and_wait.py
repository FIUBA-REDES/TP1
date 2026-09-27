import threading
from src.lib.transport import UdpTransport
from src.lib.protocol import Packet
from src.lib.stop_and_wait import StopAndWait


def test_receive():
    server = UdpTransport("127.0.0.1", 6250)
    client = UdpTransport("127.0.0.1", 6251)

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(server)

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 6250)

    packets = [
        Packet(Packet.OP_DATA, 0, 0, b"Hola "),
        Packet(Packet.OP_DATA, 1, 0, b"mundo"),
        Packet(Packet.OP_FIN, 2, 0, b"")
    ]

    for packet in packets:
        client.send(packet, server_address)

        ack, address = client.receive()

        assert ack is not None
        assert ack.opcode == Packet.OP_ACK
        assert ack.seq_num == packet.seq_num

    thread.join(timeout=2)

    assert not thread.is_alive()
    assert result["data"] == b"Hola mundo"

    client.close()
    server.close()

def test_receive_duplicate():
    server = UdpTransport("127.0.0.1", 7000)
    client = UdpTransport("127.0.0.1", 7001)

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(server)

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 7000)

    packets = [
        Packet(Packet.OP_DATA, 0, 0, b"Hola "),
        Packet(Packet.OP_DATA, 1, 0, b"mundo"),
        Packet(Packet.OP_DATA, 1, 0, b"mundo"),
        Packet(Packet.OP_FIN, 2, 0, b"")
    ]

    for packet in packets:
        client.send(packet, server_address)

        ack, address = client.receive()

        assert ack is not None
        assert ack.opcode == Packet.OP_ACK
        assert ack.seq_num == packet.seq_num

    thread.join(timeout=2)

    assert not thread.is_alive()
    assert result["data"] == b"Hola mundo"

    client.close()
    server.close()

def test_send_and_receive(tmp_path):
    server = UdpTransport("127.0.0.1", 7100)
    client = UdpTransport("127.0.0.1", 7101)

    file_path = tmp_path / "test.txt"
    file_path.write_bytes(b"Hola mundo desde Stop and Wait")

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(server)

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 7100)

    send_result = StopAndWait.send(client, file_path, server_address)

    thread.join(timeout=2)

    assert send_result is True
    assert not thread.is_alive()
    assert result["data"] == b"Hola mundo desde Stop and Wait"

    client.close()
    server.close()

class DropFirstAckTransport(UdpTransport):

    def __init__(self, host, port):
        super().__init__(host, port)
        self.drop_ack = True

    def send(self, packet, address):
        if packet.opcode == Packet.OP_ACK and self.drop_ack:
            self.drop_ack = False
            return len(packet.encode())

        return super().send(packet, address)


def test_send_and_receive_lost_ack(tmp_path):
    server = DropFirstAckTransport("127.0.0.1", 7200)
    client = UdpTransport("127.0.0.1", 7201)

    file_path = tmp_path / "test.txt"
    file_path.write_bytes(b"Hola mundo desde Stop and Wait")

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(server)

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 7200)

    send_result = StopAndWait.send(client, file_path, server_address)

    thread.join(timeout=3)

    assert send_result is True
    assert not thread.is_alive()
    assert result["data"] == b"Hola mundo desde Stop and Wait"

    client.close()
    server.close()