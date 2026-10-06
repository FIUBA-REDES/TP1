import time
import select
from .protocol import Packet

MAX_TRIES = 12       # máximo de reintentos por paquete / FIN
WINDOW_SIZE = 32     # tamaño de la ventana Selective Repeat
CHUNK_SIZE = 1024    # bytes de payload por paquete de datos
SACK_SIZE = 4        # bytes por número de secuencia en el campo SACK

INITIAL_RTO = 0.5    # retransmission timeout inicial (segundos)
ACK_POLL_TIMEOUT = 0.02   # tiempo máximo esperando ACKs entre iteraciones
FIN_ACK_WAIT = 0.05       # timeout de cada intento de ACK dentro del FIN loop
FIN_RETRY_WAIT = 0.2      # timeout esperando re-FIN del emisor tras completar
FIN_GRACE_PERIOD = 1.0    # duración total del período de gracia post-FIN
POLL_SLEEP = 0.01         # sleep del polling cuando no hay socket real


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
    def receive_with_timeout(transport, expected_address, timeout=None):
        start_time = time.time()
        has_sock = hasattr(transport, 'socket')

        while True:
            if timeout is not None:
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                    remaining = 0

                if has_sock:
                    ready, _, _ = select.select(
                        [transport.socket], [], [], remaining)
                    if not ready:
                        return None, None
                else:
                    if remaining == 0:
                        return None, None
                    time.sleep(min(POLL_SLEEP, remaining))

            packet, address = transport.receive()
            if packet is None:
                if timeout is None:
                    return None, None
            elif address[0] == expected_address[0]:
                return packet, address

            if timeout is not None and time.time() - start_time >= timeout:
                return None, None

    @staticmethod
    def receive_acks(transport, server_address, packets, base_seq, next_seq):
        while True:
            ack_packet, _ = SelectiveRepeat.receive_with_timeout(
                transport, server_address, ACK_POLL_TIMEOUT)

            if ack_packet is None:
                break
            if ack_packet.opcode != Packet.OP_ACK:
                continue

            cumulative_ack = ack_packet.ack_num
            if cumulative_ack > next_seq:
                continue

            sack_sequences = SelectiveRepeat._decode_sack(ack_packet.payload)

            for seq_num in list(packets.keys()):
                if seq_num < cumulative_ack:
                    del packets[seq_num]

            base_seq = max(base_seq, cumulative_ack)

            for seq_num in sack_sequences:
                if seq_num in packets:
                    packets[seq_num]['sacked'] = True

        return base_seq

    @staticmethod
    def check_timeouts_and_retransmit(transport, server_address, packets, RTO):
        current_time = time.time()

        for seq_num, packet_info in packets.items():
            if not packet_info['sacked']:
                time_since_sent = current_time - packet_info['time_sent']

                if time_since_sent >= RTO:
                    if packet_info['tries'] < MAX_TRIES:
                        transport.send(packet_info['packet'], server_address)
                        packet_info['time_sent'] = current_time
                        packet_info['tries'] += 1
                    else:
                        err_pkt = Packet(Packet.OP_ERROR, seq_num,
                                         0, b"Max retries reached")
                        transport.send(err_pkt, server_address)
                        return False
        return True

    @staticmethod
    def handshake_and_fin(transport, server_address, next_seq):
        fin_pkt = Packet(Packet.OP_FIN, next_seq, 0, b"")
        RTO = INITIAL_RTO

        for _ in range(MAX_TRIES):
            transport.send(fin_pkt, server_address)

            start_time = time.time()
            while time.time() - start_time < RTO:
                ack_packet, _ = SelectiveRepeat.receive_with_timeout(
                    transport, server_address, FIN_ACK_WAIT)

                if ack_packet is not None:
                    if (ack_packet.opcode == Packet.OP_ACK and
                            ack_packet.ack_num == next_seq):
                        return True

        error_packet = Packet(
            Packet.OP_ERROR,
            next_seq,
            0,
            b"Transferencia abortada por reintentos de FIN.")
        transport.send(error_packet, server_address)
        return False

    @staticmethod
    def send(transport, file_path, server_address):
        packets = {}
        next_seq = 0
        base_seq = 0
        eof = False
        RTO = INITIAL_RTO

        with open(file_path, "rb") as file:
            while not eof or packets:

                while not eof and next_seq < base_seq + WINDOW_SIZE:
                    data = file.read(CHUNK_SIZE)
                    if not data:
                        eof = True
                        break

                    pkt = Packet(Packet.OP_DATA, next_seq, 0, data)
                    transport.send(pkt, server_address)

                    packets[next_seq] = {
                        'packet': pkt,
                        'time_sent': time.time(),
                        'sacked': False,
                        'tries': 1
                    }
                    next_seq += 1

                base_seq = SelectiveRepeat.receive_acks(
                    transport, server_address, packets, base_seq, next_seq)

                if not SelectiveRepeat.check_timeouts_and_retransmit(
                        transport, server_address, packets, RTO):
                    return False

        return SelectiveRepeat.handshake_and_fin(
            transport, server_address, next_seq)

    @staticmethod
    def retry_reply_fin_ack(transport, server_address, expected_seq):
        end_time = time.time() + FIN_GRACE_PERIOD
        while time.time() < end_time:
            pkt, addr = SelectiveRepeat.receive_with_timeout(
                transport, server_address, FIN_RETRY_WAIT)
            if pkt is not None and pkt.opcode == Packet.OP_FIN:
                ack_packet = Packet(
                    Packet.OP_ACK, pkt.seq_num, expected_seq, b"")
                transport.send(ack_packet, addr)

    @staticmethod
    def receive(transport, destination_path, server_address):
        chunks = {}
        expected_seq = 0
        fin_received = False
        fin_seq = None
        consecutive_timeouts = 0

        with open(destination_path, "wb") as file:
            while True:
                packet, address = SelectiveRepeat.receive_with_timeout(
                    transport, server_address, None)

                if packet is None:
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= MAX_TRIES:
                        return False
                    continue

                server_address = address

                consecutive_timeouts = 0

                if packet.opcode == Packet.OP_DATA:
                    if packet.seq_num < expected_seq:
                        sack_payload = SelectiveRepeat._encode_sack(
                            chunks.keys())
                        ack_packet = Packet(Packet.OP_ACK, packet.seq_num,
                                            expected_seq, sack_payload)
                        transport.send(ack_packet, address)
                        continue

                    if packet.seq_num == expected_seq:
                        file.write(packet.payload)
                        expected_seq += 1

                        while expected_seq in chunks:
                            data = chunks.pop(expected_seq)
                            file.write(data)
                            expected_seq += 1

                    elif packet.seq_num > expected_seq:
                        if packet.seq_num not in chunks:
                            chunks[packet.seq_num] = packet.payload

                    sack_payload = SelectiveRepeat._encode_sack(chunks.keys())
                    ack_packet = Packet(
                        Packet.OP_ACK,
                        packet.seq_num,
                        expected_seq,
                        sack_payload)
                    transport.send(ack_packet, address)

                    if fin_received and expected_seq == fin_seq:
                        break

                elif packet.opcode == Packet.OP_FIN:
                    fin_received = True
                    fin_seq = packet.seq_num

                    sack_payload = SelectiveRepeat._encode_sack(chunks.keys())
                    ack_packet = Packet(
                        Packet.OP_ACK,
                        packet.seq_num,
                        expected_seq,
                        sack_payload)
                    transport.send(ack_packet, address)

                    if expected_seq == fin_seq:
                        break

                elif packet.opcode == Packet.OP_ERROR:
                    return False

        SelectiveRepeat.retry_reply_fin_ack(
            transport, server_address, expected_seq)
        return True
