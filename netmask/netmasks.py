from netmask.server.main import NetmaskServer
import threading
import argparse
import os

def CTRLCHandler():
	while True:
		try:
			# Create input, if user CTRL-C's this will error out
			input("")
		except:
			print("[SYSTEM] Exiting...")
			os._exit(0)

def main():
	parser = argparse.ArgumentParser(description="Netmask client interface.")
	parser.add_argument("listener4", type=str, help="The IPv4 listener interface's IP. (example: 0.0.0.0) (to set to none, use -)")
	parser.add_argument("listener6", type=str, help="The IPv6 listener interface's IP. (example: ::) (to set to none, use -)")
	parser.add_argument("--port", type=int, default=1024, help="The IPv4 listener interface's IP. (default: 1024)")
	parser.add_argument("--key", type=str, default="0", help="The communication key. (default: 0)")
	parser.add_argument("--verbose", action="store_true", help="Enable verbose mode.")
	
	args = parser.parse_args()

	threading.Thread(target=CTRLCHandler).start()

	try:
		server = NetmaskServer(args.key, args.verbose).start(args.listener4, args.listener6, args.port)
	except:
		pass


if __name__ == "__main__":
	main()
