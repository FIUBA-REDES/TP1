from .protocol import Packet

MAX_TRIES = 5

class StopAndWait:

    def send(transport, file_path, server_address):
        def send_and_wait(packet):
            for _ in range(MAX_TRIES):
                transport.send(packet, server_address)

                ack_packet, address = transport.receive()

                if (
                    ack_packet is not None
                    and address == server_address
                    and ack_packet.opcode == Packet.OP_ACK
                    and ack_packet.seq_num == packet.seq_num
                ):
                    print(f"ACK recibido: {ack_packet}")
                    return True

            return False

        with open(file_path, "rb") as file:
            data = file.read(1024)
            seq_num = 0

            while data:
                packet = Packet(
                    Packet.OP_DATA,
                    seq_num,
                    0,
                    data
                )

                if not send_and_wait(packet):
                    print(
                        "No se recibió ACK del servidor en "
                        + str(MAX_TRIES)
                        + " intentos."
                    )
                    return False

                data = file.read(1024)
                seq_num += 1

            fin_packet = Packet(
                Packet.OP_FIN,
                seq_num,
                0,
                b""
            )

            if not send_and_wait(fin_packet):
                print(
                    "No se recibió ACK del FIN en "
                    + str(MAX_TRIES)
                    + " intentos."
                )
                return False

        return True

    def receive(transport, destination_path, server_address):
        expected_seq = 0
        buffer = bytearray()

        while True:
            packet, address = transport.receive()

            if packet is None:
                continue

            if address != server_address:
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

                    with open(destination_path, "wb") as file:
                        file.write(buffer)

                    return True

                elif packet.seq_num < expected_seq:
                    packet_ack = Packet(Packet.OP_ACK, packet.seq_num, 0, b"")
                    transport.send(packet_ack, address)

            elif packet.opcode == Packet.OP_ERROR:
                print(
                    "Error del servidor: "
                    + packet.payload.decode("utf-8", errors="replace")
                )
                return False