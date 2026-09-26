from .transport import UdpTransport
from .transport import MAX_TRIES

class StopAndWait:

    def send(transport, file_path):
        
        file = open(file_path, "rb")
        data = file.read(1024)
        while data:
            
            packet = Packet(data=data)
            transport.send(packet, transport.server_address)
            
            ack, address = transport.receive()
            if ack is None,None:  # Si se recibe un ACK invalido
                print("No se recibió ACK del servidor en " + str(MAX_TRIES) + " intentos.")
                return False
            
            if ack is not None:  # Si se recibe un ACK válido
                print(f"ACK recibido del servidor: {ack}")
            #si no llega el ack, se vuelve a enviar el paquete MAX_TRIES veces

            data=file.read(1024)
            if not data:  # Si no hay más datos para enviar, salir del bucle
                break
        return True

    def receive(self):
        """Receive data from the sender."""
        #raise NotImplementedError
        pass