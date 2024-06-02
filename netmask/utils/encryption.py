import hashlib

class NetmaskEncryption:
	def __init__(self, communicationKey):
		self.communicationKey = communicationKey

		# The rolling key will change for each packet either sent by client or server
		self.rollingKeyID = 0
		self.rollingKey = hashlib.sha256(self.communicationKey).digest()

	def rollKey(self):
		self.rollingKeyID += 1
		self.rollingKey = hashlib.sha256(self.rollingKey).digest()
		
	def encryptDecrypt(self, data):
		encryptionKey = hashlib.shake_256(self.rollingKey).digest(len(data))
		return bytes([data[i] ^ encryptionKey[i % len(encryptionKey)] for i in range(len(data))])