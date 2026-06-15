
"""
Protocol Module

This module defines the communication protocol between client and server.
It specifies the structure, format, and rules for message exchange,
including message types, encoding/decoding, and data validation.

Main responsibilities:
- Define message formats and types
- Encode outgoing messages
- Decode incoming messages
- Validate message structure and content
"""
class Protocol:

    LENGTH_FIELD_SIZE = 5
    PORT = 8820

    def __init__(self, sock):
        self.sock = sock

    def create_msg(self, msg_type, *args):
        msg = msg_type + "|" + "|".join(args)
        length = str(len(msg.encode("utf-8"))).zfill(self.LENGTH_FIELD_SIZE)
        return length.encode("utf-8") + msg.encode("utf-8")

    def send_msg(self, msg_type, *args):
        msg = self.create_msg(msg_type, *args)
        self.sock.sendall(msg)

    def recv_exact(self, size):
        data = b""

        while len(data) < size:
            chunk = self.sock.recv(size - len(data))

            if not chunk:
                return None

            data += chunk

        return data

    def get_msg(self):
        length_data = self.recv_exact(self.LENGTH_FIELD_SIZE)

        if not length_data:
            return None, None

        length = length_data.decode("utf-8")

        if not length.isnumeric():
            return None, None

        msg_length = int(length)

        data = self.recv_exact(msg_length)

        print("Expected:", msg_length)
        print("Received:", len(data))

        if not data:
            return None, None

        data = data.decode("utf-8")

        parts = data.split("|")
        msg_type = parts[0]
        args = parts[1:]

        return msg_type, args

