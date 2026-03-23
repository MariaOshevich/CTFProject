import json
import os
import threading
import socket 

from Protocol import Protocol


connected_users = {}


def find_user(nickname):
    for user in users:
        if user["nickname"] == nickname:
            return user
    return None

# Accounts storage

USERS_FILE = "users.json"

if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
else:
    users = []

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)


# Tasks storage

TASKS_FILE = "tasks.json"

if os.path.exists(TASKS_FILE):
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        tasks = json.load(f)
else:
    tasks = []

    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

# List of players in the waiting room

waiting_players = []
lock = threading.Lock()

# Server

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("0.0.0.0", 9001))
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


                if any(user["nickname"] == nickname for user in users):
                    protocol.send_msg("error", "Пользователь уже существует")
                else:
                    new_user = {
                        "nickname": nickname,
                        "password": password,
                        "score": 0,
                        "opened_tasks": [],
                        "solved_tasks": []
                    }
                    users.append(new_user)

                    with open(USERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(users, f, ensure_ascii=False, indent=4)
                    protocol.send_msg("success", "Регистрация успешна")
                    print("Регистрация:", nickname, password)

            elif msg_type == "login":
                nickname = args[0]
                password = args[1]

                user = next((u for u in users if u["nickname"] == nickname), None)

                if user and user["password"] == password:
                    connected_users[client_socket] = nickname
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

            elif msg_type == "get_task_card":

                nickname = connected_users.get(client_socket)

                user = find_user(nickname)

                tasks_preview = []

                for task in tasks:
                    tasks_preview.append({
                        "id": task["id"],
                        "title": task["title"],
                        "difficulty": task["difficulty"],
                        "type": task["type"],
                        "points": task["points"],
                        "solves": task["solves"],
                    })

                data = {
                    "tasks": tasks_preview,
                    "opened_tasks": user["opened_tasks"]
                }

                protocol.send_msg("tasks_card", json.dumps(data))

            elif msg_type == "get_task_page":
                task_id = int(args[0])
                nickname = connected_users.get(client_socket)

                user = find_user(nickname)

                if task_id in user["opened_tasks"]:
                    for task in tasks:
                        if task["id"] == task_id:
                            task_page = {
                                "id": task["id"],
                                "title": task["title"],
                                "difficulty": task["difficulty"],
                                "type": task["type"],
                                "points": task["points"],
                                "solves": task["solves"],
                                "description": task["description"],
                                "files": task["files"]
                            }

                            task_json = json.dumps(task_page)
                            protocol.send_msg("tasks_page_opened", task_json)

                else:
                    protocol.send_msg("tasks_page_locked", str(task_id))

            elif msg_type == "score":

                nickname = connected_users.get(client_socket)
                user = find_user(nickname)
                user_score = user["score"]
                protocol.send_msg("your_score", str(user_score))







        except IndexError:
            protocol.send_msg("error", "Некорректные данные")
            print("Что-то не так")

    client_socket.close()


while True:

    client_socket, address = server_socket.accept()
    threading.Thread(target=handle_client, args=(client_socket, address), daemon=True).start()
