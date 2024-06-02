import netmask.impl.packets as packets
import threading
import ipaddress
import hashlib
import socket
import select
import shutil
import time
import sys
import os

# Variables
PACKET_BUFFER = 2048

class NetmaskClientGUI:
	def __init__(self, client):
		self.client = client
		self.lastUpdate = None

		# Timer for download and upload
		self.downloadSpeed = "0 B/s"
		self.uploadSpeed = "0 B/s"
		self.oldTime = time.time()

		self.currentBuffer = ""
		self.currentLineLength = 0

	def bytesToText(self, size):
		if size < 1024:
			return str(size)+" B"
		elif size < 1024**2:
			return str(round(size / 1024, 2))+" KB"
		elif size < 1024**3:
			return str(round(size / 1024**2, 2))+" MB"
		else:
			return str(round(size / 1024**3, 2))+" GB"

	def addToBuffer(self, text):
		self.currentBuffer += text
		if "\n" in text:
			self.currentLineLength = len(text.split("\n", 1)[-1])
		else:
			self.currentLineLength += len(text)

	def drawInterface(self):
		columns, rows = shutil.get_terminal_size()
		self.currentBuffer = ""

		# +--------+
		verticalBorder = "+" + ("-" * (columns - 2)) + "+"

		# |        |
		emptyLine = "|" + (" " * (columns - 2)) + "|"

		# Add first vertical border
		self.addToBuffer(verticalBorder + "\n")

		# Calculate offset on what line to put the other border
		offset = round(rows/10) # 10%

		# Make sure offset is uneven
		if offset % 2 == 0:
			offset += 1

		# Find the middle of the offset
		middleOffset = round((offset+1)/2) - 1

		for row in range(rows-2):
			try:
				if row == offset:
					# Draw top bar border
					self.addToBuffer(verticalBorder)
				elif row == middleOffset - 1:
					# Draw download and upload names
					downloadPosition = round(columns / 4)
					uploadPosition = downloadPosition * 3

					# Apply offset for text
					downloadPosition -= 4
					uploadPosition -= 3

					# Draw with the download and upload name positions
					self.addToBuffer("|")

					self.addToBuffer(" " * (downloadPosition - self.currentLineLength))

					self.addToBuffer("DOWNLOAD")

					centerOffset = ((columns - 1) // 2) - self.currentLineLength

					self.addToBuffer((" " * centerOffset) + "|")

					self.addToBuffer(" " * (uploadPosition - self.currentLineLength))

					self.addToBuffer("UPLOAD")

					self.addToBuffer((" " * (columns - self.currentLineLength - 1)) + "|")
				elif row == middleOffset + 1:
					# Draw download and upload speed
					downloadPosition = round(columns / 4)
					uploadPosition = downloadPosition * 3

					# Apply offset for text
					downloadPosition -= round(len(self.downloadSpeed)/2)
					uploadPosition -= round(len(self.uploadSpeed)/2)

					# Draw with the download and upload speed positions
					self.addToBuffer("|")
					self.addToBuffer(" " * (downloadPosition - self.currentLineLength))
					self.addToBuffer(self.downloadSpeed)

					centerOffset = ((columns - 1) // 2) - self.currentLineLength

					self.addToBuffer((" " * centerOffset) + "|")
					self.addToBuffer(" " * (uploadPosition - self.currentLineLength))
					self.addToBuffer(self.uploadSpeed)
					self.addToBuffer((" " * (columns - self.currentLineLength - 1)) + "|")

				elif row == rows - 4:
					# This is the line above the status line (which is located at the bottom)
					self.addToBuffer(verticalBorder)
					
				elif row == rows - 3:
					# This is the status line, we will get the current connection status and binded IP (if any)
					self.addToBuffer("| ")
					self.addToBuffer("STATUS: ")
					self.addToBuffer("Connected" if self.client.isConnected else "Connecting")

					if self.client.isConnected:
						self.addToBuffer(" | ")
						self.addToBuffer("IP: ")
						self.addToBuffer(self.client.bindedAddress)

					self.addToBuffer((" " * (columns - self.currentLineLength - 1)) + "|")

				elif row < offset:
					# Draw the lines to split between download and upload
					centerOffset = (columns - 1) // 2

					self.addToBuffer("|")
					self.addToBuffer((" " * (centerOffset - 1)))
					self.addToBuffer("|")
					self.addToBuffer((" " * (columns - centerOffset - 2)))
					self.addToBuffer("|")
				else:
					if len(self.client.connections) < row - offset:
						self.addToBuffer(emptyLine)
					else:
						connection = self.client.connections[row - offset - 1]

						self.addToBuffer("|")

						connectionIDString = str(connection.connectionID)
						leadingSpaces = (7 - len(connectionIDString)) // 2
						trailingSpaces = 7 - len(connectionIDString) - leadingSpaces
						self.addToBuffer(" " * leadingSpaces + connectionIDString + " " * trailingSpaces)
						self.addToBuffer("|   ")

						self.addToBuffer(str(connection.downloadedBytes))
						#connection.downloadedBytes = 0

						self.addToBuffer(" - ")

						self.addToBuffer(str(connection.uploadedBytes))
						#connection.uploadedBytes = 0

						self.addToBuffer(" " * (columns - self.currentLineLength - 1))
						self.addToBuffer("|")
			finally:
				self.addToBuffer("\n")

		self.addToBuffer(verticalBorder + "\r")
		sys.stdout.write(self.currentBuffer)


	def displayGUI(self):
		try:
			self.oldTime = time.time()

			while True:
				# Move the cursor on the top of the screen
				sys.stdout.write("\033[H")
				sys.stdout.flush()

				# Hide cursor
				sys.stdout.write("\033[?25l")
				sys.stdout.flush()

				# Sleep a bit to not consume too many CPU cycles
				time.sleep(0.03)

				# Every second, update download and upload speed
				if self.oldTime + 1 <= time.time():
					self.downloadSpeed = self.bytesToText(self.client.downloadedBytesBuffer)+"/s"
					self.uploadSpeed = self.bytesToText(self.client.uploadedBytesBuffer)+"/s"

					self.client.downloadedBytesBuffer = 0
					self.client.uploadedBytesBuffer = 0

					self.oldTime = time.time()

				# Draw the interface
				self.drawInterface()

		except KeyboardInterrupt:
			self.quitProgram()

	def quitProgram(self, text=""):
		while True:
			try:
				# Clear screen
				sys.stdout.write("\033[2J\033[H")
				sys.stdout.flush()

				# Show cursor
				sys.stdout.write("\033[?25h")
				sys.stdout.flush()

				if text != "":
					print(text)
				
				# Exit program
				os._exit(0)
			except KeyboardInterrupt:
				pass


class NetmaskClient(packets.ProtocolHandler):
	class Connection:
		connectionID = 0
		downloadedBytes = 0
		uploadedBytes = 0

	def __init__(self, communicationKey, localPort, bindMode, ipVersion, verbose = False):
		self.client = True

		self.localHost = "127.0.0.1"
		self.localPort = localPort
		self.bindMode = bindMode
		self.ipVersion = ipVersion
		self.verbose = verbose
		self.connections = []
		self.connectionCounter = 0

		self.bindedAddress = None
		self.isConnected = False

		self.gui = None
		self.host = None
		self.port = None

		self.communicationKey = str(communicationKey)
		if self.verbose:
			print("[CLIENT] Communication key is "+self.communicationKey)

	def terminateConnection(self):
		self.socket.close()
		sys.exit()

	def forwardingThreadTCP(self, uid):
		# Make connection class
		connClass = self.Connection()
		connClass.connectionID = self.connectionCounter
		self.connectionCounter += 1
		self.connections.append(connClass)

		try:
			if self.verbose:
				print("[CLIENT] Connecting to "+self.localHost+":"+str(self.localPort))

			if ipaddress.ip_network(self.localHost).version == 6:
				localConn = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			else:
				localConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

			try:
				localConn.connect((self.localHost, self.localPort))
			except:
				if self.verbose:
					print("[SYSTEM] Connection to "+self.localHost+":"+str(self.localPort)+" failed")
				return

			if self.verbose:
				print("[SYSTEM] Connecting to "+self.host+":"+str(self.port))

			# Connect to server
			if ipaddress.ip_network(self.host).version == 6:
				conn = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			else:
				conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

			try:
				conn.connect((self.host, self.port))
			except:
				if self.verbose:
					print("[SYSTEM] Connection to "+self.host+":"+str(self.port)+" failed")
				return

			# Send the mode and the UID
			conn.send(b"\x01"+uid)

			# Receive confirmation
			if conn.recv(1) != b"\x01":
				if self.verbose:
					print("[CLIENT] Forwarding socket failed.")
				return

			# Forward the connection between the two sockets
			socketList = [localConn, conn]
			shouldCloseSocket = False
			while not shouldCloseSocket:
				readSockets, writeSockets, errorSockets = select.select(socketList, [], socketList, 5000)
				if errorSockets or not readSockets:
					break
				for currentSocket in readSockets:
					oppositeSocket = socketList[1] if currentSocket == socketList[0] else socketList[0]

					data = currentSocket.recv(PACKET_BUFFER)
					if not data or data == b"":
						shouldCloseSocket = True
						break

					if currentSocket == localConn:
						if self.gui != None:
							self.downloadedBytesBuffer += len(data)
						connClass.downloadedBytes += len(data)
					else:
						if self.gui != None:
							self.uploadedBytesBuffer += len(data)
						connClass.uploadedBytes += len(data)

					oppositeSocket.sendall(data)
		except KeyboardInterrupt:
			if self.gui != None:
				while True:
					try:
						self.gui.quitProgram()
					except:
						pass
			else:
				os._exit(0)
		finally:
			self.connections.remove(connClass)

	def forwardingThreadUDP(self, uid):
		# Make connection class
		self.connectionCounter += 1
		connClass = self.Connection()
		connClass.connectionID = self.connectionCounter
		self.connections.append(connClass)

		try:
			if ipaddress.ip_network(self.localHost).version == 6:
				conn = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
			else:
				conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

			if self.verbose:
				print("[SYSTEM] Connecting to "+self.host+":"+str(self.port))

			while True:
				# Send UID
				conn.sendto(uid, (self.host, self.port))

				# Receive confirmation
				data, address = conn.recvfrom(1)
				if address != (self.host, self.port):
					continue

				if data != b"\x01":
					if self.verbose:
						print("[CLIENT] Forwarding socket failed.")
						return

				break


			# Forward the connection between the two sockets
			if self.verbose:
				print("[CLIENT] Connecting to "+self.localHost+":"+str(self.localPort))

			while True:
				data, address = conn.recvfrom(PACKET_BUFFER)

				if address == (self.host, self.port):
					conn.sendto(data, (self.localHost, self.localPort))
					if self.gui != None:
						self.downloadedBytesBuffer += len(data)
					connClass.downloadedBytes += len(data)
				elif address == (self.localHost, self.localPort):
					conn.sendto(data, (self.host, self.port))
					if self.gui != None:
						self.uploadedBytesBuffer += len(data)
					connClass.uploadedBytes += len(data)
		except KeyboardInterrupt:
			if self.gui != None:
				while True:
					try:
						self.gui.quitProgram()
					except:
						pass
			else:
				os._exit(0)
		finally:
			self.connections.remove(connClass)

	def connect(self, host, port):
		try:
			if self.gui != None:
				self.downloadedBytesBuffer = 0
				self.uploadedBytesBuffer = 0

			# Resolve the domain
			try:
				host = socket.gethostbyname(host)
			except:
				# If it's not a domain, pass
				pass

			# Check the IP version
			if ipaddress.ip_network(host).version == 6:
				conn = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			else:
				conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			
			if self.verbose:
				print("[SYSTEM] Connecting to "+host+":"+str(port))

			self.host = host
			self.port = port

			conn.settimeout(0.5)

			conn.connect((host, port))

			super().__init__(self.communicationKey, conn)
			self.socket = conn

			# Connect with mode 0
			self.socket.send(b"\x00")

			# Send handshake packet

			cHandshake = packets.CHandshakeRequest()
			cHandshake.encryptionKey = self.encryptionKey
			self.sendPacket(cHandshake)

			# Wait for server to send the proof of encryption request
			POERequest = self.recvPacket(packets.SPOERequest)

			# Send response of proof of encryption
			POEResponse = packets.CPOEResponse()
			POEResponse.proofOfEncryptionResult = hashlib.sha256(POERequest.proofOfEncryptionRequest).digest()
			self.sendPacket(POEResponse)

			# Get handshake response
			self.recvPacket(packets.SHandshakeResponse)

			if self.verbose:
				print("[CLIENT] Connection with server established successfully!")

			BindRequest = packets.CBindRequest()
			BindRequest.bindMode = self.bindMode
			BindRequest.ipVersion = self.ipVersion
			self.sendPacket(BindRequest)

			BindResponse = self.recvPacket(packets.SBindResponse)

			self.bindedAddress = BindResponse.serverIP+":"+str(BindResponse.serverPort)
			self.isConnected = True

			if self.verbose:
				print("[CLIENT] Binded on "+self.bindedAddress)
			else:
				print(self.bindedAddress)

			if BindRequest.bindMode == 0:
				while True:
					connectionPacket = self.recvPacket(packets.SConnection)
					threading.Thread(target=self.forwardingThreadTCP, args=(connectionPacket.uid,)).start()
			elif BindRequest.bindMode == 1:
				while True:
					connectionPacket = self.recvPacket(packets.SConnection)
					threading.Thread(target=self.forwardingThreadUDP, args=(connectionPacket.uid,)).start()
			
		except Exception as e:
			if self.gui != None:
				while True:
					try:
						if isinstance(e, TimeoutError):
							e = "Unable to connect to server (timed out)"
						self.gui.quitProgram(e)
					except:
						pass
			else:
				print(e)
				os._exit(0)