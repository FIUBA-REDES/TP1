from protocol import Packet

class session:

    def __init__(self, server_socket, client_socket, args=None):
        self.server_socket = server_socket
        self.client_socket = client_socket
        self.args = args
        self.chunks = {} # Para fragmentacion de paquetes
        self.buffer = bytearray() #Buffer para almacenar los datos recibidos
        self.next_seq = 0 
        self.completed = False #Caso que fin llegue antes que paquetes.

    def send_ack(self, seq_num):
        ack_packet = Packet.ack(seq_num)
        self.server_socket.sendto(ack_packet.encode(), self.client_socket)

    def start_session(self):

        # Los datos del session los crea en start-server 
        # Manda ACK
        self.packet = Packet.ack(self.packet.seq_num)
        self.server_socket.sendto(self.packet.encode(), self.client_socket)


    def update_session(self, packet):

        if packet.opcode == Packet.OP_DATA:

            # Evita duplicados
            if packet.seq_num in self.chunks:
                self._send_ack(packet.seq_num)
                return

            self.chunks[packet.seq_num] = packet.payload

            # rearmar en orden
            while self.next_seq in self.chunks:
                self.buffer.extend(self.chunks.pop(self.next_seq))
                self.next_seq += 1

            return

        # No existe un end session, porque me puede llegar el paquete de fin de sesion antes que el ultimo paquete (por ejemplo), entonces tengo que validar que tengan todos los paquetes desde 0 hasta el ultimo paquete que me llego, y si es asi, entonces puedo decir que la sesion esta completa.

        if packet.opcode == Packet.OP_FIN:
                # validar que el rango recibido sea contiguo desde 0
                expected = set(range(self.next_seq))
                if self.received == expected:
                    self.completed = True
                    self.file_bytes = bytes(self.buffer)
                    return True

                return False