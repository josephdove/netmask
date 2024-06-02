from netmask.utils.encryption import NetmaskEncryption
import hashlib
import socket
import sys
import os

class ProtocolHandler():
	client = None
	verbose = None

	def __init__(self, communicationKey, socket):
		self.communicationKey = communicationKey
		self.socket = socket

		# This encryption key will be used to check the match between client and server in the handshake request
		self.encryptionKey = hashlib.shake_256(self.communicationKey.encode()).digest(32)

		self.encryption = NetmaskEncryption(self.communicationKey.encode())

	def recv(self, length):
		while True:
			try:
				rawData = self.socket.recv(length)
				if rawData != b"":
					break
			except TimeoutError:
				continue
			except:
				if self.verbose:
					__import__("traceback").print_exc()
					print("[HANDLER] Socket got closed unexpectedly, closing connection.")

				if self.client and self.gui != None:
					self.gui.quitProgram()

				sys.exit()

		return self.encryption.encryptDecrypt(rawData)

	def recvPacket(self, expectedPacket = None):
		try:
			self.encryption.rollKey()
			rawData = self.recv(3)

			# Parse packet data
			packetId = rawData[0]
			packetLength = int.from_bytes(rawData[1:3], byteorder='big')
			if packetLength != 0:
				packetData = self.recv(packetLength)
			packet = packetList.get(packetId, None)

			# If packet ID doesn't exist, terminate connection
			if packet == None:
				self.terminateConnection()
				return

			# If packet isn't the expected packet, terminate connection
			if expectedPacket != None and packet != expectedPacket:
				self.terminateConnection()
				return

			# Create the packet instance
			packetInstance = packet()

			# If the packet data is invalid, terminate connection
			if packetLength != 0 and not packetInstance.unpackBuffer(packetData):
				self.terminateConnection()
				return

			return packetInstance
		except SystemExit:
			sys.exit()
		except:
			if self.verbose:
				__import__("traceback").print_exc()
				print("[FATAL] Couldn't recieve packet, is the communication key correct?")

			if self.client and self.gui != None:
				self.gui.quitProgram()

			self.terminateConnection()
			return

	def send(self, data):
		try:
			return self.socket.send(self.encryption.encryptDecrypt(data))
		except:
			if self.verbose:
				__import__("traceback").print_exc()
				print("[HANDLER] Socket got closed unexpectedly, closing connection.")

			if self.client and self.gui != None:
				self.gui.quitProgram()

			sys.exit()

	def sendPacket(self, packet):
		try:
			self.encryption.rollKey()

			bytesSent = self.send(packet.packMetadata())
			buffer = packet.packBuffer()
			if buffer != b"":
				bytesSent += self.send(buffer)
			return
		except SystemExit:
			sys.exit()
		except:
			if self.verbose:
				__import__("traceback").print_exc()
				print("[FATAL] Couldn't send packet, is the communication key correct?")

			if self.client and self.gui != None:
				self.gui.quitProgram()

			self.terminateConnection()
			return

	def terminateConnection(self):
		# To be overwritten
		pass

class Packet():
	packetId = 0
	packetLength = 0
	def packMetadata(self):
		return self.packetId.to_bytes(1, byteorder='big') + self.packetLength.to_bytes(2, byteorder='big')
	def unpackBuffer(self, buffer):
		return b""
	def packBuffer(self):
		return b""

class CHandshakeRequest(Packet):
	packetId = 1
	packetLength = 32
	encryptionKey = None

	def unpackBuffer(self, buffer):
		if len(buffer) != self.packetLength:
			return False
		self.encryptionKey = buffer
		return True

	def packBuffer(self):
		if len(self.encryptionKey) != self.packetLength:
			return False
		return self.encryptionKey

class SPOERequest(Packet):
	packetId = 2
	packetLength = 32
	proofOfEncryptionRequest = None

	def unpackBuffer(self, buffer):
		if len(buffer) != self.packetLength:
			return False
		self.proofOfEncryptionRequest = buffer
		return True

	def packBuffer(self):
		if len(self.proofOfEncryptionRequest) != self.packetLength:
			return False
		return self.proofOfEncryptionRequest

class CPOEResponse(Packet):
	packetId = 3
	packetLength = 32
	proofOfEncryptionResult = None

	def unpackBuffer(self, buffer):
		if len(buffer) != self.packetLength:
			return False
		self.proofOfEncryptionResult = buffer
		return True

	def packBuffer(self):
		if len(self.proofOfEncryptionResult) != self.packetLength:
			return False
		return self.proofOfEncryptionResult

class SHandshakeResponse(Packet):
	packetId = 4
	packetLength = 0

class CBindRequest(Packet):
	packetId = 5
	packetLength = 2
	
	# 1 byte: 0 for TCP, 1 for UDP
	bindMode = None

	# 1 byte: 4 for IPv4, 6 for IPv6
	ipVersion = None

	def unpackBuffer(self, buffer):
		if len(buffer) != self.packetLength:
			return False
		self.bindMode = buffer[0]
		self.ipVersion = buffer[1]

		# If bindmode isn't TCP or UDP, packet is invalid
		if self.bindMode not in [0,1]:
			return False

		# If IP version isn't 4 or 6, packet is invalid
		if self.ipVersion not in [4,6]:
			return False
		return True

	def packBuffer(self):
		if self.bindMode not in [0,1]:
			return False

		if self.ipVersion not in [4,6]:
			return False

		return self.bindMode.to_bytes(1, byteorder='big') + self.ipVersion.to_bytes(1, byteorder='big')


class SBindResponse(Packet):
	packetId = 6
	packetLength = 0

	# 4 bytes if IPv4 and 16 bytes if IPv6
	serverIP = None

	# 2 bytes
	serverPort = None

	# 4 for IPv4, 6 for IPv6, doesn't get sent
	ipVersion = 0

	def packMetadata(self):
		if self.serverIP == None:
			return self.packetId.to_bytes(1, byteorder='big') + self.packetLength.to_bytes(2, byteorder='big')

		return self.packetId.to_bytes(1, byteorder='big') + ((4 if self.ipVersion == 4 else 16) + 2).to_bytes(2, byteorder='big')

	def unpackBuffer(self, buffer):
		if len(buffer) == 6:
			ipVersion = 4
			self.serverIP = socket.inet_ntop(socket.AF_INET, buffer[2:])
		elif len(buffer) == 18:
			ipVersion = 6
			self.serverIP = socket.inet_ntop(socket.AF_INET6, buffer[2:])
		else:
			return False

		self.serverPort = int.from_bytes(buffer[:2], byteorder='big')

		return True

	def packBuffer(self):
		buffer = self.serverPort.to_bytes(2, byteorder='big')

		if self.ipVersion == 4:
			buffer += socket.inet_pton(socket.AF_INET, self.serverIP)
		elif self.ipVersion == 6:
			buffer += socket.inet_pton(socket.AF_INET6, self.serverIP)
		else:
			return False

		return buffer

class SConnection(Packet):
	packetId = 7
	packetLength = 32

	# 32 bytes
	uid = None

	def unpackBuffer(self, buffer):
		if len(buffer) != self.packetLength:
			return False
		self.uid = buffer
		return True

	def packBuffer(self):
		if len(self.uid) != self.packetLength:
			return False
		return self.uid

class SKick(Packet):
	packetId = 255
	packetLength = 0


# Packet list
packetList = {
	1: CHandshakeRequest,
	2: SPOERequest,
	3: CPOEResponse,
	4: SHandshakeResponse,
	5: CBindRequest,
	6: SBindResponse,
	7: SConnection,
	255: SKick
}
