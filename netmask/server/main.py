import netmask.impl.packets as packets
import threading
import hashlib
import asyncio
import socket
import select
import time
import sys
import os

# Variables
MAX_TIMEOUT = 5
PACKET_BUFFER = 2048

# Helper function for asyncio
def _runInThreadsafeLoop(coro):
	return asyncio.run_coroutine_threadsafe(coro, loop).result()

class AsyncTCPSocket:
	def __init__(self, reader, writer):
		self.reader = reader
		self.writer = writer

	def send(self, buffer):
		return _runInThreadsafeLoop(self._asyncSend(buffer))

	def recv(self, length):
		return _runInThreadsafeLoop(self._asyncRecv(length))

	def close(self):
		self.writer.close()

	async def _asyncSend(self, buffer):
		self.writer.write(buffer)
		await self.writer.drain()
		return len(buffer)

	async def _asyncRecv(self, length):
		return await self.reader.read(length)

class NetmaskBind:
	def __init__(self, connectionClass, bindMode, bindPort):
		self.serverSocket = None
		self.connectionClass = connectionClass
		self.bindMode = bindMode
		self.bindPort = bindPort
		self.connectedTCPClients = []
		self.UDPServers = []

	class TCPProtocol:
		def __init__(self, bindClass):
			self.server = None
			self.isForwarding = False
			self.uid = os.urandom(32)
			self.bindClass = bindClass

			self.reader = None
			self.writer = None

		async def forward(self, reader, writer):
			try:
				while True:
					data = await reader.read(PACKET_BUFFER)
					if not data:
						break
					writer.write(data)
			finally:
				writer.close()

		def setServer(self, reader, writer):
			writer.write(b"\x01")
			self.server = AsyncTCPSocket(reader, writer)

		async def killConnection(self):
			self.writer.close()
			await self.writer.wait_closed()

		async def handleClient(self, reader, writer):
			self.reader = reader
			self.writer = writer
			try:
				if not await self.bindClass.connectionClass.connectionHandler(self.uid):
					return

				timeoutCounter = 0
				while self.server == None:
					# Sleep for 10ms until we get a connection from the client
					await asyncio.sleep(0.01)

					# If timeout is reached, break and close connection
					if timeoutCounter >= round(MAX_TIMEOUT / 0.01):
						return
					timeoutCounter += 1

				# Forward forever
				self.isForwarding = True
				await asyncio.gather(self.forward(self.reader, self.server.writer), self.forward(self.server.reader, self.writer))
			finally:
				self.writer.close()
				if self.server != None:
					self.server.writer.close()
				if not self.isForwarding:
					await self.bindClass._stopServer()

	class UDPHandler(asyncio.DatagramProtocol):
		class UDPProtocol:
			def __init__(self, handlerClass, address):
				self.address = address
				self.handlerClass = handlerClass
				self.uid = os.urandom(32)
				self.buffer = []
				self.isForwarding = False

				# To be gotten on server connection
				self.forwardTransport = None
				self.forwardAddress = None

				# Create the timeout handler
				loop.create_task(self.timeoutHandler())

			async def timeoutHandler(self):
				timeoutCounter = 0
				while not self.isForwarding:
					# Sleep for 10ms until we get a connection from the client
					await asyncio.sleep(0.01)

					# If timeout is reached, close the connection
					if timeoutCounter >= round(MAX_TIMEOUT / 0.01):
						await self.handlerClass.bindClass._stopServer()
						return
					timeoutCounter += 1

			def setServer(self, forwardTransport, forwardAddress):
				# Make client acknowledge connection was successful
				forwardTransport.sendto(b"\x01", forwardAddress)

				# Send buffer (if any)
				while len(self.buffer) != 0:
					forwardTransport.sendto(self.buffer.pop(), forwardAddress)

				self.forwardTransport = forwardTransport
				self.forwardAddress = forwardAddress

				# Set the forwarding state to true
				self.isForwarding = True

		def __init__(self, bindClass):
			# List of UDPClients
			self.clients = []

			# Counter self (if we are IPv4, this is going to be IPv6, and if we are IPv6, this is going to be IPv4)
			self.counterSelf = None

			self.bindClass = bindClass

		def connection_made(self, transport):
			self.transport = transport

		def datagram_received(self, data, address):
			for client in self.clients:
				if client.address == address:
					if client.isForwarding:
						client.forwardTransport.sendto(data, client.forwardAddress)
					else:
						client.buffer.append(data)
					return

			newClient = self.UDPProtocol(self, address)
			newClient.buffer.append(data)
			self.clients.append(newClient)
			asyncio.create_task(self.bindClass.connectionClass.connectionHandler(newClient.uid))

		def killServer(self):
			if self.transport != None:
				self.transport.close()

			if self.counterSelf != None:
				self.counterSelf.transport.close()

	async def handleTCPConnection(self, reader, writer):
		try:
			tcpProtocolClass = self.TCPProtocol(self)
			self.connectedTCPClients.append(tcpProtocolClass)
			return await tcpProtocolClass.handleClient(reader, writer)
		except:
			pass

	def startServer(self):
		return _runInThreadsafeLoop(self._startServer())

	def stopServer(self):
		return _runInThreadsafeLoop(self._stopServer())

	async def _startServer(self):
		if self.bindMode == 0:
			# TCP
			sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

			# Enable dual stack for binding to both IPv4 and IPv6
			sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)

			sock.bind(("::", 0))
			sock.listen(5)
			sock.setblocking(False)

			self.serverSocket = await asyncio.start_server(self.handleTCPConnection, sock=sock)
			return self.serverSocket.sockets[0].getsockname()
		elif self.bindMode == 1:
			# UDP

			try:
				# Start IPv4 server
				_coroutine4, udpServer4 = await loop.create_datagram_endpoint(lambda: self.UDPHandler(self), local_addr=('0.0.0.0', 0))
				self.UDPServers.append(udpServer4)

				# Start IPv6 server
				_coroutine6, udpServer6 = await loop.create_datagram_endpoint(lambda: self.UDPHandler(self), local_addr=('::', _coroutine4.get_extra_info('sockname')[1]))
				self.UDPServers.append(udpServer6)

				# Define each UDP server's callbacks
				udpServer4.counterSelf = udpServer6
				udpServer6.counterSelf = udpServer4
			except:
				pass
 
			return _coroutine4.get_extra_info('sockname')


	async def _stopServer(self):
		# Kill and clear every connected TCP client
		for client in self.connectedTCPClients:
			await client.killConnection()

		self.connectedTCPClients = []

		# Shutdown and clear every UDP server
		for server in self.UDPServers:
			server.killServer()

		self.UDPServers = []

		# Remove from server's bindings
		self.connectionClass.bindings.remove(self)

		# Close the server class connection
		self.connectionClass.socket.close()

		# Close server socket
		if self.serverSocket:
			self.serverSocket.close()

class ServerConnection(packets.ProtocolHandler):
	def __init__(self, serverClass, socket):
		# This will contain all the NetmaskBinds
		self.bindings = []
		self.serverClass = serverClass
		self.verbose = False

		super().__init__(self.serverClass.communicationKey, socket)

	def terminateConnection(self):
		try:
			try:
				self.socket.send(packets.SKick().packBuffer())
			finally:
				self.socket.close()

			self.serverClass.clients.remove(self)

			for binding in self.bindings.copy():
				binding.stopServer()
		except:
			pass

		sys.exit()

	async def connectionHandler(self, uid):
		# Tell the client the UID
		connectionPacket = packets.SConnection()
		connectionPacket.uid = uid
		
		# Send packet raw because of async
		self.encryption.rollKey()
		await self.socket._asyncSend(self.encryption.encryptDecrypt(connectionPacket.packMetadata()))
		await self.socket._asyncSend(self.encryption.encryptDecrypt(connectionPacket.packBuffer()))

		return True

	def connectionThread(self):
		try:
			cHandshake = self.recvPacket(packets.CHandshakeRequest)

			# If the encryption key doesn't match, kick the client
			if cHandshake.encryptionKey != self.encryptionKey:
				self.terminateConnection()
				return

			# Send a POE request
			proofOfEncryption = os.urandom(32)
			POERequest = packets.SPOERequest()
			POERequest.proofOfEncryptionRequest = proofOfEncryption
			self.sendPacket(POERequest)

			# Get the POE response
			POEResponse = self.recvPacket(packets.CPOEResponse)

			# Check if the proof of encryption matches with the server
			if hashlib.sha256(proofOfEncryption).digest() != POEResponse.proofOfEncryptionResult:
				self.terminateConnection()
				return

			# Send handshake response
			self.sendPacket(packets.SHandshakeResponse())

			if self.verbose:
				print("[SERVER] Connection with client established successfully!")

			# Recieve the binding request

			BindRequest = self.recvPacket(packets.CBindRequest)

			# If the server doesn't have the specified IP version and if IP version is invalid, terminate connection
			if (BindRequest.ipVersion == 4 and self.serverClass.publicIPv4 == None) or (BindRequest.ipVersion == 6 and self.serverClass.publicIPv6 == None) or (BindRequest.ipVersion not in [4,6]):
				self.terminateConnection()
				return

			# NetmaskBind will take care of both TCP and UDP
			binding = NetmaskBind(self, BindRequest.bindMode, 0)
			self.bindings.append(binding)
			bindAddress = binding.startServer()

			BindResponse = packets.SBindResponse()
			BindResponse.ipVersion = BindRequest.ipVersion
			BindResponse.serverIP = self.serverClass.publicIPv4 if BindRequest.ipVersion == 4 else self.serverClass.publicIPv6
			BindResponse.serverPort = bindAddress[1]
			self.sendPacket(BindResponse)
		except:
			self.terminateConnection()
			return

class NetmaskServer:
	class UDPServer:
		def __init__(self, netmaskServer):
			self.connectedAddresses = {}
			self.netmaskServer = netmaskServer

		def connection_made(self, transport):
			self.transport = transport

		def datagram_received(self, data, address):
			if address not in self.connectedAddresses.keys() and len(data) == 32:
				# Iterate through every UID
				for client in self.netmaskServer.clients:
					for binding in client.bindings:
						for udpServer in binding.UDPServers:
							for udpClient in udpServer.clients:
								if udpClient.uid == data:
									self.connectedAddresses[address] = udpClient
									udpClient.setServer(self.transport, address)
									udpServer.transport.sendto(data, address)
									return
				
				# UID not found, close connection
				self.transport.sendto(b"\x00", address)
			elif address in self.connectedAddresses.keys():
				self.connectedAddresses[address].handlerClass.transport.sendto(data, self.connectedAddresses[address].address)

	def __init__(self, communicationKey = 0, verbose = False):
		self.client = False
		self.verbose = verbose

		# List of all the clients connected
		self.clients = []
		self.publicIPv4 = self.getPublicIPv4()
		self.publicIPv6 = self.getPublicIPv4()

		self.communicationKey = str(communicationKey)
		print("[SERVER] Communication key is "+self.communicationKey)

	def getPublicIPv4(self):
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(3)
			sock.connect(('api.ipify.org', 80))
			sock.sendall(b"GET / HTTP/1.1\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n")
			response = b""
			while True:
				data = sock.recv(4096)
				if not data:
					break
				response += data
			sock.close()
			return response.decode().split("\r\n\r\n")[1].strip()
		except:
			return None

	def getPublicIPv6(self):
		try:
			addrinfo = socket.getaddrinfo('api64.ipify.org', 80, socket.AF_INET6, socket.SOCK_STREAM)
			sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			sock.settimeout(3)
			sock.connect(addrinfo[0][4])
			sock.sendall(b"GET / HTTP/1.1\r\nHost: api64.ipify.org\r\nConnection: close\r\n\r\n")
			response = b""
			while True:
				data = sock.recv(4096)
				if not data:
					break
				response += data
			sock.close()
			return response.decode().split("\r\n\r\n")[1].strip()
		except:
			return None

	async def handleAsyncConnection(self, reader, writer):
		mode = await reader.read(1)

		# Detect if user is trying to connect or is recieving a connection
		if mode == b"\x00":
			# Call the connectionThread function in ServerConnection with a new thread that uses the AsyncTCPSocket class, which is just an emulated socket
			newClient = ServerConnection(self, AsyncTCPSocket(reader, writer))
			self.clients.append(newClient)
			threading.Thread(target=newClient.connectionThread).start()
		elif mode == b"\x01":
			# Here the user connects to recieve a connection
			uid = await reader.read(32)

			# Iterate through every UID
			for client in self.clients:
				for binding in client.bindings:
					for connectedClient in binding.connectedTCPClients:
						if connectedClient.uid == uid:
							connectedClient.setServer(reader, writer)
							return
			
			writer.close()
		else:
			writer.close()
		
	async def startAsync(self, ipv4host, ipv6host, port):
		# Create IPv4 socket
		if ipv4host != "-":
			sock4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock4.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock4.bind((ipv4host, port))
			sock4.listen(5)
			sock4.setblocking(False)

			print("[SYSTEM] Started listening for TCP on "+ipv4host+":"+str(port))

			await asyncio.start_server(self.handleAsyncConnection, sock=sock4)

		# Create IPv6 socket
		if ipv6host != "-":
			sock6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			sock6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock6.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
			sock6.bind((ipv6host, port))
			sock6.listen(5)
			sock6.setblocking(False)

			print("[SYSTEM] Started listening for TCP on "+ipv6host+":"+str(port))

			await asyncio.start_server(self.handleAsyncConnection, sock=sock6)

		try:
			# Start IPv4 UDP server
			if ipv4host != "-":
				_coroutine4, udpServer4 = await loop.create_datagram_endpoint(lambda: self.UDPServer(self), local_addr=(ipv4host, port))
				print("[SYSTEM] Started listening for UDP on "+ipv4host+":"+str(port))

			# Start IPv6 UDP server
			if ipv6host != "-":
				_coroutine6, udpServer6 = await loop.create_datagram_endpoint(lambda: self.UDPServer(self), local_addr=(ipv6host, port))
				print("[SYSTEM] Started listening for UDP on "+ipv6host+":"+str(port))
		except:
			pass

	def start(self, ipv4host, ipv6host, port):
		global loop
		loop = asyncio.get_event_loop()
		loop.run_until_complete(self.startAsync(ipv4host, ipv6host, port))
		loop.run_forever()