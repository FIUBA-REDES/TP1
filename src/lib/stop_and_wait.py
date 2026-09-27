from .transport import UdpTransport
from .protocol import Packet

MAX_TRIES = 5

class StopAndWait:

    def send(transport, file_path, server_address):
        
        file = open(file_path, "rb")
        data = file.read(1024)
        packet = Packet(Packet.OP_DATA, 0, 0, data)
        while data:
            
        
            ack = None
            for _ in range(MAX_TRIES):
                transport.send(packet, server_address)
                ack, address = transport.receive()
                if ack is not None:
                    print(f"ACK recibido del servidor: {ack}")
                    break

            if ack is None:
                print("No se recibió ACK del servidor en " + str(MAX_TRIES) + " intentos.")
                return False

            data=file.read(1024)
            if not data:  # Si no hay más datos para enviar, salir del bucle
                break
            packet = Packet(Packet.OP_DATA, packet.seq_num + 1, 0, data)
        return True

    def receive(self):
        """Receive data from the sender."""
        #raise NotImplementedError
        pass