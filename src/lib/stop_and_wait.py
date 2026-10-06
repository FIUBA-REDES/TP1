import logging
from .protocol import Packet

MAX_TRIES = 5
FIN_TIMEOUT = 0.5  # Tiempo de espera para recibir un ACK del FIN
CHUNK_SIZE = 1024  # Tamaño de cada chunk de datos a enviar

class StopAndWait:

    def send(transport, file_path, server_address):
        def send_and_wait(packet):
            for _ in range(MAX_TRIES):
                logging.debug(
                    f"Enviando paquete seq={packet.seq_num} "
                )

                transport.send(packet, server_address)
                ack_packet, address = transport.receive()
                if (
                    ack_packet is not None
                    and address == server_address
                    and ack_packet.opcode == Packet.OP_ACK
                    and ack_packet.seq_num == packet.seq_num
                ):
                    logging.debug(
                        f"ACK recibido seq={ack_packet.seq_num}"
                    )
                    return True
            return False

        with open(file_path, "rb") as file:
            data = file.read(CHUNK_SIZE)
            seq_num = 0
            ack_num = 0

            while data:
                if seq_num != 0:
                    ack_num = seq_num - 1
                packet = Packet(
                    Packet.OP_DATA,
                    seq_num,
                    ack_num,
                    data
                )
                if not send_and_wait(packet):
                    logging.error(
                        "No se recibió ACK del servidor en "
                        + str(MAX_TRIES)
                        + " intentos."
                    )
                    # Enviar OP_ERROR antes de abortar
                    err_pkt = Packet(
                        Packet.OP_ERROR,
                        packet.seq_num,
                        0,
                        b"Transferencia abortada por reintentos de datos.")
                    transport.send(err_pkt, server_address)
                    return False

                data = file.read(CHUNK_SIZE)
                seq_num += 1

            fin_packet = Packet(
                Packet.OP_FIN,
                seq_num,
                ack_num + 1,
                b""
            )
            if not send_and_wait(fin_packet):
                logging.error(
                    "No se recibió ACK del FIN en "
                    + str(MAX_TRIES)
                    + " intentos."
                )
                # NUEVO: Enviar OP_ERROR antes de abortar
                err_pkt = Packet(
                    Packet.OP_ERROR,
                    seq_num,
                    0,
                    b"Transferencia abortada por reintentos de FIN.")
                transport.send(err_pkt, server_address)
                return False

        return True

    def receive(transport, destination_path, server_address):
        expected_seq = 0
        buffer = bytearray()
        consecutive_timeouts = 0

        while True:
            packet, address = transport.receive()

            # Si hay timeout, sumamos al contador.
            if packet is None:
                consecutive_timeouts += 1
                if consecutive_timeouts >= MAX_TRIES:
                    logging.error("Error: Conexión interrumpida, "
                                  "se superó el límite de timeouts.")
                    return False
                continue

            # Reiniciamos el contador porque llegó un paquete válido
            consecutive_timeouts = 0

            if address != server_address:
                continue

            if packet.opcode == Packet.OP_DATA:
                ack_num = packet.seq_num
                if packet.seq_num == expected_seq:
                    buffer.extend(packet.payload)
                    packet_ack = Packet(
                        Packet.OP_ACK, packet.seq_num, ack_num, b"")
                    transport.send(packet_ack, address)
                    expected_seq += 1
                elif packet.seq_num < expected_seq:
                    packet_ack = Packet(
                        Packet.OP_ACK, packet.seq_num, ack_num, b"")
                    transport.send(packet_ack, address)

            elif packet.opcode == Packet.OP_FIN:
                if packet.seq_num == expected_seq:
                    # Escribimos el archivo final en disco
                    with open(destination_path, "wb") as file:
                        file.write(buffer)

                    # Mandamos el primer ACK confirmando el FIN
                    packet_ack = Packet(Packet.OP_ACK, packet.seq_num, 0, b"")
                    transport.send(packet_ack, address)

                    # Esperamos brevemente por si el ACK se perdió
                    transport.set_timeout(FIN_TIMEOUT)
                    for _ in range(MAX_TRIES):
                        extra_pkt, extra_addr = transport.receive()
                        if extra_pkt is None:
                            # Si el timeout expira sin recibir nada, el emisor
                            # cerró con éxito.
                            break
                        if (extra_addr == server_address and
                                extra_pkt.opcode == Packet.OP_FIN):
                            # Si vuelve a llegar el FIN, reenviamos el ACK.
                            transport.send(packet_ack, address)

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
