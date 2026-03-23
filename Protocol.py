
class Protocol:

    LENGTH_FIELD_SIZE = 2
    PORT = 8820

    def __init__(self, sock):
        self.sock = sock

    def create_msg(self, msg_type, *args):
        msg = msg_type + "|" + "|".join(args)
        return msg.encode("utf-8")

    def send_msg(self, msg_type, *args):
        msg = self.create_msg(msg_type, *args)
        self.sock.sendall(msg)

    def get_msg(self):
        data = self.sock.recv(1024).decode("utf-8")
        if not data:
            return None, None
        parts = data.split("|")
        msg_type = parts[0]
        args = parts[1:]
        return msg_type, args
