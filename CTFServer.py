import json
import os
import threading
import socket 
from Protocol import Protocol


# Accounts storage

USERS_FILE = "users.json"

if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
else:
    users = {}  # {"nickname": "password"}

# List of players in the waiting room

waiting_players = []
lock = threading.Lock()

# Server

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
server_socket.bind(("0.0.0.0", 9000)) 
server_socket.listen() 

print("Server started...")

def handle_client(client_socket, address):
    print("Client connected:", address)
    protocol = Protocol(client_socket)

    while True:
        msg_type, args = protocol.get_msg()
        if not msg_type:
            print("Client disconnected")
            break  

        try:
            if msg_type == "signup":
                nickname = args[0]
                password = args[1]

                if nickname in users:
                    protocol.send_msg("error", "Пользователь уже существует")
                else:
                    users[nickname] = password
                    with open(USERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(users, f, ensure_ascii=False, indent=4)
                    protocol.send_msg("success", "Регистрация успешна")
                    print("Регистрация:", nickname, password)

            elif msg_type == "login":
                nickname = args[0]
                password = args[1]

                if nickname in users and users[nickname] == password:
                    protocol.send_msg("success", "Login is done")
                    print("Пользователь вошел:", nickname)
                else:
                    protocol.send_msg("error", "Неверный логин или пароль")

            elif msg_type == "find_match":
                if len(waiting_players) == 0:
                    waiting_players.append(client_socket)
                    protocol.send_msg("wait", "Waiting for the second player")
                    print(f"Player {args[0]} is in the waiting room, waiting for the second player")
                else:
                    opponent=waiting_players.pop(0)

                    opponent_protocol = Protocol(opponent)

                    opponent_protocol.send_msg("start", "Game started")
                    protocol.send_msg("start", "Game started")

                    print("Game started")


        except IndexError:
            protocol.send_msg("error", "incorrect data")
            print("Что-то не так")

    client_socket.close()


while True:

    client_socket, address = server_socket.accept()
    threading.Thread(target=handle_client, args=(client_socket, address), daemon=True).start()

