import socket
import os


class abs_dir(object):
    def __init__(self, path):
        abspath = path
        if not os.path.isabs(path):
            abspath = os.path.abspath(path)
        if not os.path.isabs(abspath):
            raise ValueError("expected abs path, but got '%s'" % abspath)
        if os.path.isdir(abspath):
            self.parent = abspath
        else:
            self.parent = os.path.dirname(abspath)
    def __div__(self, relpath):
        return os.path.join(self.parent, relpath)


def send_at_9999(data):
    HOST, PORT = "localhost", 9999

    # Create a socket (SOCK_STREAM means a TCP socket)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to server and send data
        sock.connect((HOST, PORT))
        sock.sendall(data + "\n")

        # Receive data from the server and shut down
        received = sock.recv(1024)
    except socket.error as error:
        pass  # silently ignore the error
    finally:
        sock.close()
