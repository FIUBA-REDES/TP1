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
    #HEADER_SIZE = 11 # [1(Opcode) + 4(Seq) + 4(Ack) + 2(PayloadLen)]

#Un paquete tiene de campos: HEADER + PAYLOAD
#HEADER = [OPCODE(1 Byte) + SEQNUMBER(4 Bytes) + ACKNUMBER(4 Bytes) + PAYLOAD_LENGHT(2 Bytes)]
#Tamaño del Header = 11bits
    def __init__(self, opcode: int, seq_num: int, ack_num:int, payload: bytes):
        self.opcode = opcode
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.payload_len = len(payload)
        self.payload = payload 

# Convierte un paquete en bytes crudos en un paquete para enviar por el socket.
    def encode(self) -> bytes:
        header = ( 
            self.opcode.to_bytes(length = Packet.OPCODE_SIZE, byteorder="big") +
            self.seq_num.to_bytes(length = Packet.SEQ_SIZE, byteorder="big") +
            self.ack_num.to_bytes(length = Packet.ACK_SIZE, byteorder="big") +
            self.payload_len.to_bytes(length = Packet.LENGTH_SIZE, byteorder="big")
        )
        return header + self.payload
      
##TODO: Falta terminar esta función para decodear 
# Convierte una secuencia de bytes en un paquete
    def decode(cls, raw_bytes: bytes): #Es otro constructor
        raw_bytes[0:2]
        opcode = int.from_bytes(raw_bytes[0:Packet.OPCODE_SIZE], byteorder="big")
        seq_num = int.from_bytes(raw_bytes[Packet.OPCODE_SIZE:(Packet.OPCODE_SIZE+Packet.SEQ_SIZE)], byteorder="big")
        ack_num = int.from_bytes()

        return Packet(opcode=opcode, seq_num=seq_num, ack_num=ack_num, payload=) 
    
        

def handshake_start() -> Packet:
    return Packet(opcode=Packet.OP_START, seq_num=0, ack_num=0, payload=b'')

def handshake_ack(seq_num: int) -> Packet:
    return Packet(opcode=Packet.OP_ACK, seq_num=seq_num, ack_num=0, payload=b'')

def session_end(seq_num: int) -> Packet:
    return Packet(opcode=Packet.OP_FIN, seq_num=seq_num, ack_num=0, payload=b'')





