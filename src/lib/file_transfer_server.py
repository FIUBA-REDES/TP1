import os
from .protocol import Packet, ack
from .session import Session
from .transport import UdpTransport
from .stop_and_wait import StopAndWait
from .sack import SelectiveRepeat
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


class FileTransferServer:
    """Server skeleton for receiving file transfer requests over UDP."""

    def __init__(self, host="127.0.0.1", port=5005,
                 timeout=None, storage_dir="storage"):
        self.address = (host, port)
        self.transport = UdpTransport(timeout=timeout)
        self.sessions = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.lock = Lock()
        self.running = False
        self.storage_dir = storage_dir

        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

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

            if packet is not None:
                self.handle_packet(packet, client_address)

    def handle_packet(self, packet, client_address):
        """Register a new client and dispatch its packet."""
        with self.lock:
            # 1. Si la sesión ya existe para este cliente, encolar el paquete
            # en su sesión.
            if client_address in self.sessions:
                self.sessions[client_address].enqueue(packet)
                return

            # 2. Si es un cliente nuevo iniciando conexión
            if packet.opcode == Packet.OP_START:
                client_session = Session(
                    self.transport, client_address, self.storage_dir)
                self.sessions[client_address] = client_session
                payload_str = packet.payload.decode("utf-8", errors="ignore")

                # 1. Si es solicitud de DOWNLOAD
                if payload_str.startswith("DOWNLOAD:"):
                    file_name = payload_str[len("DOWNLOAD:"):]
                    file_path = os.path.join(self.storage_dir, file_name)
                    if not os.path.isfile(file_path):
                        err_pkt = Packet(Packet.OP_ERROR, packet.seq_num,
                                         0, b"Archivo no encontrado")
                        self.transport.send(err_pkt, client_address)
                        del self.sessions[client_address]
                        return

                    # Confirmar inicio de descarga
                    self.transport.send(ack(packet.seq_num), client_address)
                    # Ejecutar el envío hacia el cliente en el pool de threads
                    self.executor.submit(
                        self._worker_task,
                        client_session,
                        "DOWNLOAD",
                        "sw",
                        file_path,
                        client_address)
                    return

                # 2. Si es solicitud de UPLOAD (o tests con payload vacio)
                client_session.start_session(packet)
                self.executor.submit(client_session.process_packets)
                return

    def _worker_task(self, client_session, action,
                     protocol, path, client_address):
        # Tarea que ejecuta el protocolo de transferencia en un hilo separado.
        try:
            if protocol == "sw":
                if action == "DOWNLOAD":
                    StopAndWait.send(client_session, path, client_address)
                elif action == "UPLOAD":
                    StopAndWait.receive(client_session, path, client_address)

            elif protocol == "sack":
                if action == "DOWNLOAD":
                    SelectiveRepeat.send(client_session, path, client_address)
                elif action == "UPLOAD":
                    SelectiveRepeat.receive(
                        client_session, path, client_address)
        finally:
            # Una vez finalizada la transferencia, borramos la sesión
            with self.lock:
                if client_address in self.sessions:
                    del self.sessions[client_address]

    def stop(self):
        """Stop receiving packets and close the UDP transport."""
        self.running = False
        with self.lock:
            for client_session in self.sessions.values():
                client_session.enqueue(None)
        self.executor.shutdown(wait=True)
        self.transport.close()
