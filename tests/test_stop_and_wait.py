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
    # Se esperan MAX_TRIES intentos de datos + 1 envío final del OP_ERROR
    assert transport.send_count == MAX_TRIES + 1








# Este test simula un emisor que envía un solo bloque de datos y luego se desconecta
# abruptamente sin enviar el OP_FIN. Si el test falla, StopAndWait.receive() entra
# en un bucle while True eterno con continue.
def test_receive_aborts_on_timeout_limit(tmp_path):
    server = UdpTransport("127.0.0.1", 7700, timeout=0.1)
    client = UdpTransport("127.0.0.1", 7701, timeout=0.1)
    destination = tmp_path / "abandoned.txt"
    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(
            server, destination, ("127.0.0.1", 7701)
        )

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 7700)
    try:
        # El cliente manda 1 bloque y luego abandona la comunicación
        packet = Packet(Packet.OP_DATA, 0, 0, b"Bloque inicial")
        client.send(packet, server_address)
        ack, _ = client.receive()
        assert ack is not None and ack.opcode == Packet.OP_ACK

        # Esperamos que el receptor agote los MAX_TRIES (5 * 0.1s = ~0.5s) y salga
        thread.join(timeout=2.0)
        assert not thread.is_alive(), "El receptor se quedó en bucle infinito"
        assert result["data"] is False
    finally:
        client.close()
        server.close()


class RecordingNoAckTransport:
    def __init__(self):
        self.sent_packets = []

    def send(self, packet, address):
        self.sent_packets.append(packet)
        return len(packet.encode())

    def receive(self, buffer_size=65535):
        return None, None

# Este test fuerza al emisor a agotar sus MAX_TRIES simulando una red que no responde.
# Verifica que, antes de abortar silenciosamente, el emisor construya y envíe 
# un paquete de tipo OP_ERROR para avisarle al receptor que se canceló la transferencia.
def test_send_notifies_op_error_on_max_retries(tmp_path):
    transport = RecordingNoAckTransport()
    file_path = tmp_path / "abort_test.bin"
    file_path.write_bytes(b"Datos no confirmados")

    # Ejecutamos el envío, que fallará tras 5 intentos
    result = StopAndWait.send(transport, file_path, ("127.0.0.1", 7800))

    assert result is False
    # Filtramos los paquetes enviados buscando el OP_ERROR
    error_packets = [
        p for p in transport.sent_packets if p.opcode == Packet.OP_ERROR
    ]
    assert len(error_packets) > 0, "No se envió paquete OP_ERROR al agotar reintentos"


class DropFinAckTransport(UdpTransport):
    def __init__(self, host, port, timeout=0.2):
        super().__init__(host, port, timeout=timeout)
        self.drop_fin_ack = True

    def send(self, packet, address):
        # Descartamos únicamente el primer ACK que confirma el FIN
        if packet.opcode == Packet.OP_ACK and self.drop_fin_ack:
            # Si el seq_num es 1 (el seq del FIN tras 1 paquete de datos)
            if packet.seq_num == 1:
                self.drop_fin_ack = False
                return len(packet.encode())
        return super().send(packet, address)


# Este test verifica que si el último ACK (que confirma el OP_FIN) se pierde en la red,
# el receptor no cierre su socket inmediatamente. Debe quedarse en un estado TIME_WAIT
# para escuchar la retransmisión del OP_FIN por parte del emisor y reenviar el ACK.
def test_fin_retransmission_handled_by_receiver(tmp_path):
    server = DropFinAckTransport("127.0.0.1", 7900, timeout=0.2)
    client = UdpTransport("127.0.0.1", 7901, timeout=0.2)
    file_path = tmp_path / "fin_test.txt"
    destination = tmp_path / "fin_received.txt"
    file_path.write_bytes(b"Contenido de prueba FIN")

    result = {}

    def server_receive():
        result["data"] = StopAndWait.receive(
            server, destination, ("127.0.0.1", 7901)
        )

    thread = threading.Thread(target=server_receive)
    thread.start()

    server_address = ("127.0.0.1", 7900)
    try:
        send_result = StopAndWait.send(client, file_path, server_address)
        thread.join(timeout=3.0)

        assert send_result is True, "El emisor falló porque no recibió el ACK retransmitido"
        assert result["data"] is True
        assert destination.read_bytes() == file_path.read_bytes()
    finally:
        client.close()
        server.close()