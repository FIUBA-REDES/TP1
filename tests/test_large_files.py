import os
import threading
import pytest
from lib.transport import UdpTransport
from lib.sack import SelectiveRepeat
from lib.stop_and_wait import StopAndWait


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
    Prueba la transferencia de un archivo pesado usando Selective Repeat (SACK).
    Verifica que no haya desbordamiento de números de secuencia, truncamiento ni corrupción.
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
