import os
from .protocol import Packet
from .session import Session
from .transport import UdpTransport
from .stop_and_wait import StopAndWait
from .sack import SelectiveRepeat
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


class FileTransferServer:

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

    def _cleanup_session(self, session):
        """Callback invoked by Session when it finishes or aborts."""
        if session.aborted:
            with self.lock:
                self.sessions.pop(session.client_address, None)

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

    def set_protocol_and_file_name_from_payload(self, payload_str):

        if payload_str.startswith("DOWNLOAD:"):
            parts = payload_str.split(":", 2)
            if len(parts) == 3 and parts[1] in ("sw", "sack"):
                req_protocol = parts[1]
                file_name = parts[2]
            else:
                req_protocol = "sw"
                file_name = payload_str[len("DOWNLOAD:"):]
        elif payload_str.startswith("UPLOAD:"):
            parts = payload_str.split(":", 2)
            if len(parts) == 3 and parts[1] in ("sw", "sack"):
                req_protocol = parts[1]
                file_name = parts[2]
            else:
                req_protocol = "sw"
                file_name = payload_str[len("UPLOAD:"):]
        else:
            req_protocol = "sw"
            file_name = payload_str

        return req_protocol, file_name

    def verify_and_execute_type_of_new_packet(self, packet, client_address):

        client_session = Session(
            self.transport,
            client_address,
            self.storage_dir,
            on_close=self._cleanup_session,
        )

        self.sessions[client_address] = client_session
        payload_str = packet.payload.decode("utf-8", errors="ignore")

        # Payload vacío: modo test, sin transferencia real
        if not payload_str:
            client_session.start_session(packet)
            self.executor.submit(client_session.process_packets)
            return

        req_protocol, file_name = self.set_protocol_and_file_name_from_payload(
            payload_str)

        # 1. Si es solicitud de DOWNLOAD
        if payload_str.startswith("DOWNLOAD:"):

            file_path = os.path.join(self.storage_dir, file_name)
            if not os.path.isfile(file_path):
                err_pkt = Packet(
                    Packet.OP_ERROR,
                    packet.seq_num,
                    0,
                    b"Archivo no encontrado")
                self.transport.send(err_pkt, client_address)
                del self.sessions[client_address]
                return

            client_session.start_session(packet)

            # Ejecutar el envío hacia el cliente en el pool de threads
            self.executor.submit(
                self._worker_task,
                self.transport,
                "DOWNLOAD",
                req_protocol,
                file_path,
                client_address)
            return

        # 2. Si es solicitud de UPLOAD
        # Los paquetes llegan via enqueue() → process_packets() los ensambla y
        # guarda
        client_session.remote_name = file_name
        client_session.start_session(packet)
        self.executor.submit(client_session.process_packets)
        return

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
                self.verify_and_execute_type_of_new_packet(
                    packet, client_address)
                return

    def _worker_task(self, transport, action,
                     protocol, path, client_address):
        """Ejecuta el protocolo de DOWNLOAD en un hilo separado"""
        sender_transport = UdpTransport(timeout=1.0)
        try:
            if protocol == "sw":
                StopAndWait.send(sender_transport, path, client_address)
            elif protocol == "sack":
                SelectiveRepeat.send(sender_transport, path, client_address)
        finally:
            sender_transport.close()

    def stop(self):
        """Stop receiving packets and close the UDP transport."""
        self.running = False
        with self.lock:
            for client_session in self.sessions.values():
                client_session.enqueue(None)
        self.executor.shutdown(wait=True)
        self.transport.close()
