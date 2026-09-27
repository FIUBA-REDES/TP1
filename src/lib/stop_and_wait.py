from .transport import UdpTransport
from .transport import MAX_TRIES
from .protocol import Packet

class StopAndWait:

    def send(transport, file_path, server_address):
        
        file = open(file_path, "rb")
        data = file.read(1024)
        packet = Packet(Packet.OP_DATA, 0, 0, data)
        while data:
            
        
            transport.send(packet, server_address)
            
            ack, address = transport.receive()
            if ack is None and address is None:  # Si se recibe un ACK invalido
                print("No se recibió ACK del servidor en " + str(MAX_TRIES) + " intentos.")
                return False
            
            if ack is not None:  # Si se recibe un ACK válido
                print(f"ACK recibido del servidor: {ack}")
            #si no llega el ack, se vuelve a enviar el paquete MAX_TRIES veces

            data=file.read(1024)
            if not data:  # Si no hay más datos para enviar, salir del bucle
                break
            packet = Packet(Packet.OP_DATA, packet.seq_num + 1, 0, data)
        return True

    def receive(self):
        """Receive data from the sender."""
        #raise NotImplementedError
        pass