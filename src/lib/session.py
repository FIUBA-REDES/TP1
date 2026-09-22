class session:


    def __init__(self,
                 server_socket=None,
                 client_socket=None,
                 packet=None,
                 args=None):
        self.server_socket = server_socket
        self.client_socket = client_socket
        self.packet = packet
        self.args = args
        
    def start_session(self):
        
        self.packet = Packet.ack(self.packet.seq_num)
        self.server_socket.sendto(self.packet.encode(), self.client_socket)
        
        self.server_socket.receivefrom(1024)
        self.packet = Packet.decode(data)

    def update_session(self, packet):
        self.packet = packet
        ack_packet = Packet.ack(self.packet.seq_num)
        self.server_socket.sendto(ack_packet.encode(), self.client_socket)

    def end_session(self):
        self.packet = Packet.fin(self.packet.seq_num)
        self.server_socket.sendto(self.packet.encode(), self.client_socket)