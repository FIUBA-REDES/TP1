from .protocol import Packet

MAX_TRIES = 5
WINDOW_SIZE = 32
CHUNK_SIZE = 1024
SACK_SIZE = 4


class SelectiveRepeat:

    @staticmethod
    def _encode_sack(sequences):
        payload = bytearray()

        for seq_num in sorted(sequences):
            payload.extend(seq_num.to_bytes(SACK_SIZE, byteorder="big"))

        return bytes(payload)

    @staticmethod
    def _decode_sack(payload):
        if len(payload) % SACK_SIZE != 0:
            return set()

        sequences = set()

        for offset in range(0, len(payload), SACK_SIZE):
            seq_num = int.from_bytes(
                payload[offset:offset + SACK_SIZE],
                byteorder="big"
            )
            sequences.add(seq_num)

        return sequences

    @staticmethod
    def send(transport, file_path, server_address):
        with open(file_path, "rb") as file:
            packets = {}
            next_seq = 0
            base_seq = 0
            eof = False
            tries = 0

            while not eof or packets:
                while not eof and next_seq < base_seq + WINDOW_SIZE:
                    data = file.read(CHUNK_SIZE)

                    if not data:
                        eof = True
                        break

                    packets[next_seq] = Packet(
                        Packet.OP_DATA,
                        next_seq,
                        0,
                        data
                    )
                    next_seq += 1

                for packet in packets.values():
                    transport.send(packet, server_address)

                if not packets:
                    break

                ack_packet, address = transport.receive()

                if ack_packet is None:
                    tries += 1

                    if tries >= MAX_TRIES:
                        print(
                            "No se recibieron ACKs en "
                            + str(MAX_TRIES)
                            + " intentos."
                        )
                        return False

                    continue

                if address != server_address:
                    continue

                if ack_packet.opcode == Packet.OP_ERROR:
                    print(
                        "Error del servidor: "
                        + ack_packet.payload.decode(
                            "utf-8",
                            errors="replace"
                        )
                    )
                    return False

                if ack_packet.opcode != Packet.OP_ACK:
                    continue

                tries = 0

                cumulative_ack = ack_packet.ack_num
                sack_sequences = SelectiveRepeat._decode_sack(
                    ack_packet.payload
                )

                acknowledged = set()

                for seq_num in packets:
                    if seq_num < cumulative_ack:
                        acknowledged.add(seq_num)

                acknowledged.update(sack_sequences)

                for seq_num in acknowledged:
                    packets.pop(seq_num, None)

                while base_seq not in packets and base_seq < next_seq:
                    base_seq += 1

            fin_packet = Packet(
                Packet.OP_FIN,
                next_seq,
                next_seq,
                b""
            )

            for _ in range(MAX_TRIES):
                transport.send(fin_packet, server_address)

                ack_packet, address = transport.receive()

                if (
                    ack_packet is not None
                    and address == server_address
                    and ack_packet.opcode == Packet.OP_ACK
                    and ack_packet.seq_num == fin_packet.seq_num
                ):
                    return True

            print(
                "No se recibió ACK del FIN en "
                + str(MAX_TRIES)
                + " intentos."
            )

            error_packet = Packet(
                Packet.OP_ERROR,
                fin_packet.seq_num,
                0,
                b"Transferencia abortada por reintentos de FIN."
            )
            transport.send(error_packet, server_address)

            return False

    @staticmethod
    def receive(transport, destination_path, server_address):
        chunks = {}
        next_seq = 0
        fin_seq = None
        buffer = bytearray()
        consecutive_timeouts = 0

        while True:
            packet, address = transport.receive()

            if packet is None:
                consecutive_timeouts += 1

                if consecutive_timeouts >= MAX_TRIES:
                    print(
                        "Error: Conexión interrumpida, se superó "
                        "el límite de timeouts."
                    )
                    return False

                continue

            consecutive_timeouts = 0

            if address != server_address:
                continue

            if packet.opcode == Packet.OP_DATA:
                if packet.seq_num not in chunks and packet.seq_num >= next_seq:
                    chunks[packet.seq_num] = packet.payload

                while next_seq in chunks:
                    buffer.extend(chunks.pop(next_seq))
                    next_seq += 1

                sack_payload = SelectiveRepeat._encode_sack(chunks.keys())

                ack_packet = Packet(
                    Packet.OP_ACK,
                    packet.seq_num,
                    next_seq,
                    sack_payload
                )

                transport.send(ack_packet, address)

                if fin_seq is not None and next_seq == fin_seq:
                    with open(destination_path, "wb") as file:
                        file.write(buffer)

                    return True

            elif packet.opcode == Packet.OP_FIN:
                fin_seq = packet.seq_num

                sack_payload = SelectiveRepeat._encode_sack(chunks.keys())

                ack_packet = Packet(
                    Packet.OP_ACK,
                    packet.seq_num,
                    next_seq,
                    sack_payload
                )

                transport.send(ack_packet, address)

                if next_seq == fin_seq:
                    with open(destination_path, "wb") as file:
                        file.write(buffer)

                    return True

            elif packet.opcode == Packet.OP_ERROR:
                print(
                    "Error del servidor: "
                    + packet.payload.decode(
                        "utf-8",
                        errors="replace"
                    )
                )
                return False