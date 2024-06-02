from netmask.client.main import NetmaskClient, NetmaskClientGUI
import threading
import argparse
import os

def main():
	parser = argparse.ArgumentParser(description="Netmask client interface.")
	parser.add_argument("bindMode", type=str, choices=["tcp","udp"], help="The bind mode.")
	parser.add_argument("port", type=int, help="The port number.")
	parser.add_argument("ipVersion", type=int, choices=[4,6], help="The IP version.")
	parser.add_argument("server", type=str, help="The server (example: 127.0.0.1:1024).")
	parser.add_argument("--key", type=str, default="0", help="The communication key (default: 0).")
	parser.add_argument("--verbose", action="store_true", help="Enable verbose mode.")
	parser.add_argument("--nogui", action="store_true", help="Disable GUI in verbose mode.")
	
	args = parser.parse_args()

	try:
		host, port = args.server.split(":")
		port = int(port)
	except:
		parser.print_help()
		os._exit(1)
	
	if args.verbose and not args.nogui:
		parser.error("Verbose mode requires --nogui to be specified.")

	server = NetmaskClient(args.key, args.port, 0 if args.bindMode == "tcp" else 1, args.ipVersion, verbose=args.verbose)
	
	if not args.nogui:
		gui = NetmaskClientGUI(server)
		server.gui = gui
		threading.Thread(target=NetmaskClientGUI(server).displayGUI).start()
	
	server.connect(host, port)

if __name__ == "__main__":
	main()
