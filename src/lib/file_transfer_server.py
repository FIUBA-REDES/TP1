import os
from .protocol import Packet, ack
from .session import Session
from .transport import UdpTransport
from .stop_and_wait import StopAndWait
from .sack import SelectiveRepeat
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

class FileTransferServer:
    def __init__(self, host="127.0.0.1", port=5005, timeout=None, storage_dir="storage"):
        self.address = (host, port)
        self.transport = UdpTransport(timeout=timeout)
        self.sessions = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.lock = Lock()
        self.running = False
        self.storage_dir = storage_dir
        
        # Crear directorio si no existe
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def start(self):
        self.transport.bind(*self.address)
        self.running = True

    def serve_forever(self):
        if not self.running:
            self.start()

        while self.running:
            packet, client_address = self.transport.receive()

            if packet is not None:
                with self.lock:
                    # Si ya existe una sesión para este cliente, le pasamos el paquete a su cola
                    if client_address in self.sessions:
                        self.sessions[client_address].enqueue((packet, client_address))
                    
                    # Si es un cliente nuevo iniciando una conexión
                    elif packet.opcode == Packet.OP_START:
                        self.handle_new_request(packet, client_address)

    def handle_new_request(self, packet, client_address):
        """Procesa un OP_START, crea una sesión y lanza un hilo para atenderla."""
        try:
            request = packet.payload.decode("utf-8")
            action, protocol, remote_name = request.split(":", 2)
            path = os.path.join(self.storage_dir, remote_name)
        except ValueError:
            return  # Paquete malformado

        # Validaciones para DOWNLOAD
        if action == "DOWNLOAD" and not os.path.isfile(path):
            error_packet = Packet(Packet.OP_ERROR, packet.seq_num, 0, b"El archivo no existe.")
            self.transport.send(error_packet, client_address)
            return

        # Acusar recibo del OP_START
        self.transport.send(ack(packet.seq_num), client_address)

        # Crear la sesión (Session debe actuar como un "transport" falso que lee de su propia cola)
        client_session = Session(self.transport, client_address)
        self.sessions[client_address] = client_session

        # Lanzar el hilo trabajador
        self.executor.submit(self._worker_task, client_session, action, protocol, path, client_address)

    def _worker_task(self, client_session, action, protocol, path, client_address):
        """Tarea que ejecuta el protocolo de transferencia en un hilo separado."""
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
                    SelectiveRepeat.receive(client_session, path, client_address)
        finally:
            # Limpiar la sesión al terminar
            with self.lock:
                if client_address in self.sessions:
                    del self.sessions[client_address]

    def stop(self):
        self.running = False
        with self.lock:
            for client_session in self.sessions.values():
                client_session.enqueue((None, None))  # Señal de fin para destrabar colas
        self.executor.shutdown(wait=True)
        self.transport.close()