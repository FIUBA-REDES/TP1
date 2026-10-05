import os
import time
import random
import threading
import pytest
from lib.transport import UdpTransport
from lib.sack import SelectiveRepeat
from lib.stop_and_wait import StopAndWait


class SimulatedLossDelayTransport(UdpTransport):
    """
    Transporte UDP que simula un canal con pérdida de paquetes y latencia (RTT).
    - loss_rate: probabilidad (0.0 a 1.0) de descartar un paquete saliente.
    - delay_ms: retardo unidireccional en milisegundos (RTT / 2).
    """
    def __init__(self, host=None, port=None, timeout=None, loss_rate=0.10, delay_ms=20):
        super().__init__(host, port, timeout)
        self.loss_rate = loss_rate
        self.delay_sec = delay_ms / 1000.0

    def send(self, packet, address):
        # Simulación de pérdida de paquetes (10% por defecto)
        if random.random() < self.loss_rate:
            return len(packet.encode())

        # Simulación de retardo de ida/vuelta (half-RTT por tramo)
        if self.delay_sec > 0:
            def delayed_send():
                time.sleep(self.delay_sec)
                try:
                    super(SimulatedLossDelayTransport, self).send(packet, address)
                except Exception:
                    pass

            t = threading.Thread(target=delayed_send, daemon=True)
            t.start()
            return len(packet.encode())

        return super().send(packet, address)


def generate_large_file(path, size_bytes):
    """Genera un archivo con datos pseudo-aleatorios deterministas / por bloques."""
    chunk = os.urandom(64 * 1024)  # Bloques de 64KB en memoria
    written = 0
    with open(path, "wb") as f:
        while written < size_bytes:
            to_write = min(len(chunk), size_bytes - written)
            f.write(chunk[:to_write])
            written += to_write


@pytest.mark.parametrize("file_size_mb", [1, 5])
def test_sack_large_file_transfer(tmp_path, file_size_mb):
    """
    Prueba la transferencia de un archivo pesado usando Selective Repeat (SACK)
    en condiciones ideales (sin pérdida simulada).
    """
    size_bytes = file_size_mb * 1024 * 1024
    src_file = tmp_path / f"source_{file_size_mb}mb.bin"
    dst_file = tmp_path / f"dest_{file_size_mb}mb.bin"

    generate_large_file(src_file, size_bytes)

    server = UdpTransport("127.0.0.1", 8100, timeout=1.0)
    client = UdpTransport("127.0.0.1", 8101, timeout=1.0)

    result = {}

    def server_receive():
        result["success"] = SelectiveRepeat.receive(
            server, dst_file, ("127.0.0.1", 8101)
        )

    server_thread = threading.Thread(target=server_receive)
    server_thread.start()

    try:
        sent_ok = SelectiveRepeat.send(client, src_file, ("127.0.0.1", 8100))
        server_thread.join(timeout=30.0)

        assert not server_thread.is_alive(), "El servidor no terminó a tiempo"
        assert sent_ok is True, "El cliente emisor falló al enviar"
        assert result.get("success") is True, "El servidor receptor falló al recibir"

        assert dst_file.exists()
        assert dst_file.stat().st_size == size_bytes, "El tamaño del archivo recibido no coincide"
        assert dst_file.read_bytes() == src_file.read_bytes(), "El contenido del archivo difiere del original"
    finally:
        client.close()
        server.close()


def test_sack_5mb_under_loss_and_rtt_constraint(tmp_path):
    """
    Requisito del enunciado:
    Las operaciones de carga/descarga deben completarse en menos de 2 minutos para
    archivos de prueba de tamaño 5 MB (usando el protocolo con SACK, y con la red
    configurada a un 10 % de pérdida y un RTT de 40 ms).
    """
    file_size_mb = 5
    size_bytes = file_size_mb * 1024 * 1024
    src_file = tmp_path / "source_5mb_lossy.bin"
    dst_file = tmp_path / "dest_5mb_lossy.bin"

    generate_large_file(src_file, size_bytes)

    # RTT = 40 ms => 20 ms por tramo (unidireccional). Pérdida = 10%
    server = SimulatedLossDelayTransport(
        "127.0.0.1", 8300, timeout=1.0, loss_rate=0.10, delay_ms=20
    )
    client = SimulatedLossDelayTransport(
        "127.0.0.1", 8301, timeout=1.0, loss_rate=0.10, delay_ms=20
    )

    result = {}

    def server_receive():
        result["success"] = SelectiveRepeat.receive(
            server, dst_file, ("127.0.0.1", 8301)
        )

    server_thread = threading.Thread(target=server_receive)
    start_time = time.time()
    server_thread.start()

    try:
        sent_ok = SelectiveRepeat.send(client, src_file, ("127.0.0.1", 8300))
        server_thread.join(timeout=120.0)
        elapsed_time = time.time() - start_time

        assert not server_thread.is_alive(), "El servidor superó el timeout de 2 minutos"
        assert elapsed_time < 120.0, f"La transferencia tardó {elapsed_time:.2f}s, superando el límite de 2 minutos (120s)"
        assert sent_ok is True, "El cliente emisor falló al enviar con 10% pérdida y 40ms RTT"
        assert result.get("success") is True, "El servidor receptor falló al recibir"

        assert dst_file.exists()
        assert dst_file.stat().st_size == size_bytes, "El tamaño del archivo recibido no coincide"
        assert dst_file.read_bytes() == src_file.read_bytes(), "El contenido del archivo difiere del original tras pérdida y retransmisiones"
    finally:
        client.close()
        server.close()


def test_stop_and_wait_large_file_transfer(tmp_path):
    """
    Prueba la transferencia de un archivo moderadamente grande (256 KB = 256 paquetes)
    usando Stop-and-Wait para validar integridad en transferencias con muchos paquetes.
    """
    size_bytes = 256 * 1024
    src_file = tmp_path / "source_saw_256kb.bin"
    dst_file = tmp_path / "dest_saw_256kb.bin"

    generate_large_file(src_file, size_bytes)

    server = UdpTransport("127.0.0.1", 8200, timeout=1.0)
    client = UdpTransport("127.0.0.1", 8201, timeout=1.0)

    result = {}

    def server_receive():
        result["success"] = StopAndWait.receive(
            server, dst_file, ("127.0.0.1", 8201)
        )

    server_thread = threading.Thread(target=server_receive)
    server_thread.start()

    try:
        sent_ok = StopAndWait.send(client, src_file, ("127.0.0.1", 8200))
        server_thread.join(timeout=20.0)

        assert not server_thread.is_alive(), "El servidor no terminó a tiempo"
        assert sent_ok is True, "El cliente emisor falló al enviar"
        assert result.get("success") is True, "El servidor receptor falló al recibir"

        assert dst_file.exists()
        assert dst_file.stat().st_size == size_bytes, "El tamaño del archivo recibido no coincide"
        assert dst_file.read_bytes() == src_file.read_bytes(), "El contenido del archivo difiere del original"
    finally:
        client.close()
        server.close()
