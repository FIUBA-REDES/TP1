
import os
from upload import LAST_WELL_KNOWN_PORT


def verify_client_args(args):
    """Verify the command-line arguments for the client."""

    if args.host is None:
        print("Error: The server IP address is not specified.")
        return


    if  is None:
        print("Error: The server port is not specified.")
        return
    else:
        if port_servidor <= LAST_WELL_KNOWN_PORT or port_servidor > 65535:
            print("Error: The server port is not valid.")
            return




    if os.path.isfile(args.src) == False:
        print(f"Error: The source file '{args.src}' does not exist.")
        return


    name_archivo = args.name
    if name_archivo is None:
        print(f"Error: The name of the file to be sent is not specified.")
        return
    
    protocolo = args.protocol
    if protocolo not in ["stop-and-wait", "go-back-n", "selective-repeat"]:
        print("Error: Invalid protocol. Please choose one of the following: stop-and-wait, go-back-n, selective-repeat")
        return