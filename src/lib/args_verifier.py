import ipaddress
import os
LAST_WELL_KNOWN_PORT = 1023
MAX_PORT = 65535
COLLECTION_OF_NOT_KNOWN_USED_PORTS = (8080,)
VALID_PROTOCOLS = ("stop-and-wait", "go-back-n", "selective-repeat")


def verify_server_address(host, port):
    """Verify that a host and port can be used by the application."""
    if host is None or not isinstance(host, str) or not host.strip():
        print("Error: The server host is not specified.")
        return False

    try:
        address = ipaddress.ip_address(host.strip())
    except ValueError:
        print("Error: The server host is not a valid IP address.")
        return False

    if not isinstance(address, ipaddress.IPv4Address):
        print("Error: The server host must be an IPv4 address.")
        return False

    if port is None:
        print("Error: The server port is not specified.")
        return False

    if not isinstance(port, int) or isinstance(port, bool):
        print("Error: The server port is not valid.")
        return False

    if port <= LAST_WELL_KNOWN_PORT or port > MAX_PORT:
        print("Error: The server port is not valid.")
        return False

    if port in COLLECTION_OF_NOT_KNOWN_USED_PORTS:
        print("Error: The server port is not valid.")
        return False

    return True


def verify_client_args(args):
    """Verify the command-line arguments for upload or download."""
    if not verify_server_address(args.host, args.port):
        return False

    if hasattr(args, "src") and args.src is not None:
        if os.path.isdir(args.src):
            print(f"Error: The source path '{args.src}' is a directory.")
            return False
        if os.path.isfile(args.src) == False:
            print(f"Error: The source file '{args.src}' does not exist.")
            return False
    elif hasattr(args, "dst") and args.dst is not None:
        if os.path.isdir(args.dst):
            print(f"Error: The destination path '{args.dst}' is a directory.")
            return False
        destination_directory = os.path.dirname(args.dst) or "."
        if not os.path.isdir(destination_directory):
            print(
                f"Error: The destination directory "
                f"'{destination_directory}' does not exist."
            )
            return False
    else:
        print("Error: A source or destination file is required.")
        return False




    if not isinstance(args.name, str) or not args.name.strip():
        print("Error: The file name is not specified.")
        return False
    if os.path.basename(args.name) != args.name:
        print("Error: The file name must not contain directories.")
        return False

    if args.protocol not in VALID_PROTOCOLS:
        print(
            "Error: Invalid protocol. Please choose one of the following: "
            "stop-and-wait, go-back-n, selective-repeat"
        )
        return False

    return True


def verify_server_args(args):
    """Verify the command-line arguments for the server."""
    if verify_server_address(args.host, args.port) == False:
        return False

    return True

