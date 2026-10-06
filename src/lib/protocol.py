class Packet:
    # Constantes de OPCODES
    OP_START = 0  # Inicio de conexión
    OP_DATA = 1   # Fragmento de archivo
    OP_ACK = 2    # Confirmación
    OP_FIN = 3    # Fin de archivo
    OP_ERROR = 4  # Error

    OPCODE_SIZE = 1
    SEQ_SIZE = 4
    ACK_SIZE = 4
    LENGTH_SIZE = 2

    HEADER_SIZE = OPCODE_SIZE + SEQ_SIZE + ACK_SIZE + LENGTH_SIZE
    # HEADER_SIZE = 11 # [1(Opcode) + 4(Seq) + 4(Ack) + 2(PayloadLen)]

# Un paquete tiene de campos: HEADER + PAYLOAD
# HEADER = [OPCODE(1 Byte) + SEQNUMBER(4 Bytes) + ...
# ACKNUMBER(4 Bytes) + PAYLOAD_LENGHT(2 Bytes)]

# Tamaño del Header = 11bytes
    def __init__(self, opcode: int, seq_num: int,
                 ack_num: int, payload: bytes):
        self.opcode = opcode
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.payload_len = len(payload)
        self.payload = payload

# Convierte un paquete en bytes crudos en un paquete para enviar por el socket.
    def encode(self) -> bytes:
        header = (
            self.opcode.to_bytes(length=Packet.OPCODE_SIZE, byteorder="big") +
            self.seq_num.to_bytes(length=Packet.SEQ_SIZE, byteorder="big") +
            self.ack_num.to_bytes(length=Packet.ACK_SIZE, byteorder="big") +
            self.payload_len.to_bytes(
                length=Packet.LENGTH_SIZE, byteorder="big")
        )
        return header + self.payload

# Convierte una secuencia de bytes en un paquete
    @classmethod
    def decode(cls, raw_bytes: bytes):  # Es otro constructor
        if len(raw_bytes) < cls.HEADER_SIZE:
            raise ValueError("Paquete truncado: header incompleto.")
        opcode = int.from_bytes(raw_bytes[0:cls.OPCODE_SIZE], byteorder="big")
        seq_num = int.from_bytes(raw_bytes[cls.OPCODE_SIZE:(
            cls.OPCODE_SIZE + cls.SEQ_SIZE)], byteorder="big")
        ack_num = int.from_bytes(raw_bytes[(cls.OPCODE_SIZE + cls.SEQ_SIZE):(
            cls.OPCODE_SIZE + cls.SEQ_SIZE + cls.ACK_SIZE)], byteorder="big")
        payload_len = int.from_bytes(
            raw_bytes[cls.HEADER_SIZE - cls.LENGTH_SIZE:cls.HEADER_SIZE],
            byteorder="big")

        if opcode not in (cls.OP_START, cls.OP_DATA,
                          cls.OP_ACK, cls.OP_FIN, cls.OP_ERROR):
            raise ValueError(f"Opcode inválido: {opcode}.")

        if len(raw_bytes) != cls.HEADER_SIZE + payload_len:
            raise ValueError("Payload incompleto o longitud inválida.")

        payload = raw_bytes[cls.HEADER_SIZE:]

        return cls(opcode=opcode, seq_num=seq_num,
                   ack_num=ack_num, payload=payload)

# Maneja el ack de selective acknowledgment (SACK). Crea un paquete de ACK
# con el número de secuencia más alto recibido y una lista de los números
# de secuencia recibidos fuera de orden.
    @staticmethod
    def sack_ack(next_seq, received):
        payload = b"".join(
            seq.to_bytes(Packet.SEQ_SIZE, byteorder="big")
            for seq in sorted(received)
        )

        return Packet(
            opcode=Packet.OP_ACK,
            seq_num=0,
            ack_num=next_seq,
            payload=payload
        )

# Decodifica un paquete de ACK con SACK. Devuelve el número de secuencia
# más alto recibido y una lista de los números de secuencia recibidos
# fuera de orden.
    def decode_sack(packet):
        if packet.opcode != Packet.OP_ACK:
            raise ValueError("El paquete no es un ACK.")

        if len(packet.payload) % Packet.SEQ_SIZE != 0:
            raise ValueError("Payload SACK inválido.")

        received = []

        for i in range(0, len(packet.payload), Packet.SEQ_SIZE):
            seq_num = int.from_bytes(
                packet.payload[i:i + Packet.SEQ_SIZE],
                byteorder="big"
            )
            received.append(seq_num)

        return packet.ack_num, received


def handshake_start(payload=b"") -> Packet:
    return Packet(opcode=Packet.OP_START, seq_num=0,
                  ack_num=0, payload=payload)


def ack(seq_num: int) -> Packet:
    return Packet(opcode=Packet.OP_ACK, seq_num=seq_num,
                  ack_num=seq_num, payload=b'')


def session_end(seq_num: int) -> Packet:
    return Packet(opcode=Packet.OP_FIN, seq_num=seq_num,
                  ack_num=seq_num, payload=b'')
