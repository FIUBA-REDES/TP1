from .transport import UdpTransport
from .protocol import Packet

MAX_TRIES = 5

class StopAndWait:

    def send(transport, file_path, server_address):
        
        file = open(file_path, "rb")
        data = file.read(1024)
        packet = Packet(Packet.OP_DATA, 0, 0, data)
        
        while data:
            
            ack_ok = False

            for _ in range(MAX_TRIES):
                transport.send(packet, server_address)
                ack, address = transport.receive()

                if ack is not None and address == server_address and ack.opcode == Packet.OP_ACK and ack.seq_num == packet.seq_num:
                    #valida que el ACK recibido es del servidor y tiene el número de secuencia correcto
                    print(f"ACK recibido del servidor: {ack}")
                    ack_ok = True
                    break

            if not ack_ok:
                print("No se recibió ACK del servidor en " + str(MAX_TRIES) + " intentos.")
                return False

            data = file.read(1024)

            # Envio y rececpcion del paquete FIN cuando no hay más datos para enviar
            if not data:
                packet = Packet(Packet.OP_FIN, packet.seq_num + 1, 0, b"")
                
                ack_ok = False

                for _ in range(MAX_TRIES):
                    transport.send(packet, server_address)
                    ack, address = transport.receive()

                    if ack is not None and address == server_address and ack.opcode == Packet.OP_ACK and ack.seq_num == packet.seq_num:
                        print(f"ACK recibido del FIN: {ack}")
                        ack_ok = True
                        break

                if not ack_ok:
                    print("No se recibió ACK del FIN en " + str(MAX_TRIES) + " intentos.")
                    return False

                break
            
            packet = Packet(Packet.OP_DATA, packet.seq_num + 1, 0, data)

        file.close()
        return True

    def receive(transport):
        expected_seq = 0
        buffer = bytearray()
        client_address = None

        while True:
            packet, address = transport.receive()

            if packet is None:
                continue

            if client_address is None:
                client_address = address

            if address != client_address:
                continue

            if packet.opcode == Packet.OP_DATA:
                if packet.seq_num == expected_seq:
                    buffer.extend(packet.payload)

                    packet_ack = Packet(Packet.OP_ACK, packet.seq_num, 0, b"")
                    transport.send(packet_ack, address)

                    expected_seq += 1

                elif packet.seq_num < expected_seq:
                    packet_ack = Packet(Packet.OP_ACK, packet.seq_num, 0, b"")
                    transport.send(packet_ack, address)

            elif packet.opcode == Packet.OP_FIN:
                if packet.seq_num == expected_seq:
                    packet_ack = Packet(Packet.OP_ACK, packet.seq_num, 0, b"")
                    transport.send(packet_ack, address)

                    return bytes(buffer)

                elif packet.seq_num < expected_seq:
                    packet_ack = Packet(Packet.OP_ACK, packet.seq_num, 0, b"")
                    transport.send(packet_ack, address)