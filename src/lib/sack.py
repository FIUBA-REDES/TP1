import time
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
    def receive_with_timeout(transport, expected_address, timeout=0.02):
        start_time = time.time()
        while True:
            packet, address = transport.receive()
            if packet is not None and address == expected_address:
                return packet, address

            if time.time() - start_time >= timeout:
                return None, None

    @staticmethod
    def receive_acks(transport, server_address, packets, base_seq):
        while True:
            ack_packet, _ = SelectiveRepeat.receive_with_timeout(transport, server_address, 0.0)
            
            if ack_packet is None:
                break
            if ack_packet.opcode != Packet.OP_ACK:
                continue

            cumulative_ack = ack_packet.ack_num
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
                        print(f"Error: Se superó el límite de reintentos para paquete {seq_num}.")
                        return False
        return True

    @staticmethod
    def handshake_and_fin(transport, server_address, next_seq):
        fin_pkt = Packet(Packet.OP_FIN, next_seq, 0, b"")
        RTO = 0.5

        for _ in range(MAX_TRIES):
            transport.send(fin_pkt, server_address)
            
            start_time = time.time()
            while time.time() - start_time < RTO:
                ack_packet, _ = SelectiveRepeat.receive_with_timeout(transport, server_address, 0.05)
                
                if ack_packet is not None:
                    if ack_packet.opcode == Packet.OP_ACK and ack_packet.ack_num == next_seq:
                        return True

        print("Error: No se recibió ACK del FIN en los intentos permitidos.")
        error_packet = Packet(Packet.OP_ERROR, next_seq, 0, b"Transferencia abortada por reintentos de FIN.")
        transport.send(error_packet, server_address)
        return False

    @staticmethod
    def send(transport, file_path, server_address):
        packets = {}
        next_seq = 0
        base_seq = 0
        eof = False
        RTO = 0.5  

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

                base_seq = SelectiveRepeat.receive_acks(transport, server_address, packets, base_seq)
                
                if not SelectiveRepeat.check_timeouts_and_retransmit(transport, server_address, packets, RTO):
                    return False  

        return SelectiveRepeat.handshake_and_fin(transport, server_address, next_seq)

    @staticmethod
    def retry_reply_fin_ack(transport, server_address, expected_seq):
        end_time = time.time() + 1.5
        while time.time() < end_time:
            pkt, addr = SelectiveRepeat.receive_with_timeout(transport, server_address, 0.2)
            if pkt is not None and pkt.opcode == Packet.OP_FIN:
                ack_packet = Packet(Packet.OP_ACK, pkt.seq_num, expected_seq, b"")
                transport.send(ack_packet, addr)

    @staticmethod
    def receive(transport, destination_path, server_address):
        chunks = {}
        expected_seq = 0
        fin_received = False
        fin_seq = None
        consecutive_timeouts = 0
        RTO = 1.0

        with open(destination_path, "wb") as file:
            while True:
                packet, address = SelectiveRepeat.receive_with_timeout(transport, server_address, RTO)

                if packet is None:
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= MAX_TRIES:
                        print("Error: Conexión interrumpida, se superó el límite de timeouts.")
                        return False
                    continue

                consecutive_timeouts = 0

                if packet.opcode == Packet.OP_DATA:
                    if packet.seq_num < expected_seq:
                        sack_payload = SelectiveRepeat._encode_sack(chunks.keys())
                        ack_packet = Packet(Packet.OP_ACK, packet.seq_num, expected_seq, sack_payload)
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
                    ack_packet = Packet(Packet.OP_ACK, packet.seq_num, expected_seq, sack_payload)
                    transport.send(ack_packet, address)

                    if fin_received and expected_seq == fin_seq:
                        break

                elif packet.opcode == Packet.OP_FIN:
                    fin_received = True
                    fin_seq = packet.seq_num

                    sack_payload = SelectiveRepeat._encode_sack(chunks.keys())
                    ack_packet = Packet(Packet.OP_ACK, packet.seq_num, expected_seq, sack_payload)
                    transport.send(ack_packet, address)

                    if expected_seq == fin_seq:
                        break

                elif packet.opcode == Packet.OP_ERROR:
                    print("Error del servidor:", packet.payload.decode("utf-8", errors="replace"))
                    return False

        SelectiveRepeat.retry_reply_fin_ack(transport, server_address, expected_seq)

        return True