import socket

from .protocol import Packet

MAX_TRIES = 5

# Permite importarla desde stop_and_wait con:
# from .transport import MAX_TRIES
__all__ = ["UdpTransport", "MAX_TRIES"]

class UdpTransport:
	
	def __init__(self, host=None, port=None, timeout=None):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		if timeout is not None:
			self.socket.settimeout(timeout)
		if host is not None and port is not None:
			self.bind(host, port)

	def bind(self, host, port):
		self.socket.bind((host, port))

	def send(self, packet, address):
		return self.socket.sendto(packet.encode(), address)


	def try_receive(self, buffer_size=65535):
		self.socket.settimeout(0.5)
		try:
			data, address = self.socket.recvfrom(buffer_size)
			return Packet.decode(data), address

		except socket.timeout:
			return None, None



	def receive(self, buffer_size=65535):

		tries = 0
		while tries < MAX_TRIES:
			try_receive = self.try_receive(buffer_size)
			if try_receive[0] is not None:
				return try_receive
			tries += 1

		return None, None

		
		data, address = self.socket.recvfrom(buffer_size)
		return Packet.decode(data), address

	def set_timeout(self, timeout):
		self.socket.settimeout(timeout)

	def close(self):
		self.socket.close()
