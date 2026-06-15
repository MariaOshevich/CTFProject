"""
Server Module

This module implements the server-side logic of the system.
It is responsible for accepting client connections, processing incoming requests,
managing system data, and sending appropriate responses back to clients.

Main responsibilities:
- Handle multiple client connections
- Process requests according to protocol rules
- Manage system state and data storage interaction
- Send encoded/encrypted responses to clients
"""

# =====================================================================
# 1. IMPORTS
# =====================================================================

import json
import os
import random
import socket
import threading
import time


# SECURITY MODULE
from Security import RSAKeyExchange, SymmetricCipher, DataHasher
from cryptography.hazmat.primitives import serialization

# PROTOCOL MODULE
from Protocol import Protocol


class Server:

    MATCH_TIME = 3 * 60
    USERS_FILE = "users.json"
    TASKS_FILE = "tasks.json"
    ROUNDS_FILE = "rounds.json"
    HISTORY_FILE = "history.json"

    def __init__(self, host="0.0.0.0", port=5555):
        self.host = host
        self.port = port

        # Server state
        self.connected_users = {}
        self.matches = {}
        self.game_scores = {}
        self.match_history = {}
        self.waiting_players = []
        self.client_ciphers = {}

        # In-memory database
        self.users = []
        self.tasks = []
        self.rounds = []

        # Thread lock
        self.lock = threading.Lock()

        # Socket initialization
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def init_server_storage(self):
        if os.path.exists(self.USERS_FILE):
            with open(self.USERS_FILE, "r", encoding="utf-8") as f:
                self.users = json.load(f)
        else:
            self.users = []
            with open(self.USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.users, f, ensure_ascii=False, indent=4)

        if os.path.exists(self.TASKS_FILE):
            with open(self.TASKS_FILE, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
        else:
            self.tasks = []
            with open(self.TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=4)

        if os.path.exists(self.ROUNDS_FILE):
            with open(self.ROUNDS_FILE, "r", encoding="utf-8") as f:
                rounds_data = json.load(f)
        else:
            rounds_data = {"rounds": []}
        self.rounds = rounds_data["rounds"]

        if not os.path.exists(self.HISTORY_FILE):
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

        with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
            self.match_history = json.load(f)

    def find_user(self, nickname):
        for user in self.users:
            if user["nickname"] == nickname:
                return user
        return None

    def save_user(self, updated_user):
        with open(self.USERS_FILE, "r") as f:
            self.users = json.load(f)

        for i, user in enumerate(self.users):
            if user["nickname"] == updated_user["nickname"]:
                self.users[i] = updated_user
                break

        with open(self.USERS_FILE, "w") as f:
            json.dump(self.users, f, indent=4)

    def save_tasks(self, updated_tasks):
        with open(self.TASKS_FILE, "r", encoding="utf-8") as f:
            current_tasks = json.load(f)

        updated_map = {t["id"]: t for t in updated_tasks}

        for i, task in enumerate(current_tasks):
            task_id = task.get("id")
            if task_id in updated_map:
                current_tasks[i] = updated_map[task_id]

        with open(self.TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_tasks, f, indent=4, ensure_ascii=False)

    def save_match_result(self, player1_nick, player2_nick, winner, player1_score, player2_score, time_left):
        match_data_p1 = {
            "opponent": player2_nick,
            "winner": winner,
            "my_score": player1_score,
            "enemy_score": player2_score,
            "time": time_left
        }

        match_data_p2 = {
            "opponent": player1_nick,
            "winner": winner,
            "my_score": player2_score,
            "enemy_score": player1_score,
            "time": time_left
        }

        if player1_nick not in self.match_history:
            self.match_history[player1_nick] = []

        if player2_nick not in self.match_history:
            self.match_history[player2_nick] = []

        self.match_history[player1_nick].append(match_data_p1)
        self.match_history[player2_nick].append(match_data_p2)

        self.match_history[player1_nick] = self.match_history[player1_nick][-6:]
        self.match_history[player2_nick] = self.match_history[player2_nick][-6:]

        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.match_history, f, indent=4)

    def generate_match_round(self, player1_nick, player2_nick):
        player1 = self.find_user(player1_nick)
        player2 = self.find_user(player2_nick)

        available_rounds = []
        for round_data in self.rounds:
            round_id = round_data["id"]
            if (round_id not in player1["opened_rounds"] and
                    round_id not in player2["opened_rounds"]):
                available_rounds.append(round_data)

        if not available_rounds:
            return None, None

        chosen_round = random.choice(available_rounds)

        player1["opened_rounds"].append(chosen_round["id"])
        player2["opened_rounds"].append(chosen_round["id"])

        self.save_user(player1)
        self.save_user(player2)

        round_tasks = []
        for task in self.tasks:
            if task["id"] in chosen_round["tasks"]:
                task_copy = task.copy()
                task_copy.pop("flag", None)
                round_tasks.append(task_copy)

        return chosen_round, round_tasks

    def match_timer(self, player_socket):
        time.sleep(self.MATCH_TIME)

        match = self.matches.get(player_socket)
        if not match or not match.get("active", True):
            return

        self.finish_match(player_socket)

    def player_completed_round(self, user, round_tasks):
        for task_id in round_tasks:
            if task_id not in user["solved_tasks"]:
                return False
        return True

    def finish_match(self, player_socket, winner_socket=None):
        # Protect the function from simultaneous execution in different threads
        with self.lock:
            # Check whether the match exists
            if player_socket not in self.matches:
                return

            match = self.matches[player_socket]
            # Check the active flag in case another thread acquired the lock
            if not match.get("active", True):
                return

            opponent_socket = match["opponent"]

            # Mark as inactive inside the lock so other threads cannot enter
            match["active"] = False
            if opponent_socket in self.matches:
                self.matches[opponent_socket]["active"] = False

            # Collect scores
            player_score = self.game_scores.get(player_socket, 0)
            opponent_score = self.game_scores.get(opponent_socket, 0)

            player_protocol = Protocol(player_socket)
            opponent_protocol = Protocol(opponent_socket)

            player_nick = self.connected_users.get(player_socket) or "Disconnected_Player"
            opponent_nick = self.connected_users.get(opponent_socket) or "Opponent"

            # Winner determination logic
            if winner_socket is not None:
                if winner_socket == player_socket:
                    player_result = "win"
                    opponent_result = "lose"
                    winner_nick = player_nick
                else:
                    player_result = "lose"
                    opponent_result = "win"
                    winner_nick = opponent_nick
            else:
                if player_score > opponent_score:
                    player_result = "win"
                    opponent_result = "lose"
                    winner_nick = player_nick
                elif player_score < opponent_score:
                    player_result = "lose"
                    opponent_result = "win"
                    winner_nick = opponent_nick
                else:
                    player_result = "draw"
                    opponent_result = "draw"
                    winner_nick = "Draw"

            start_time = match.get("start_time", time.time())
            match_duration = int(time.time() - start_time)

            # Saving results
            self.save_match_result(player_nick, opponent_nick, winner_nick, player_score, opponent_score,
                                   match_duration)
            print(f"Match result saved to history for {player_nick} and {opponent_nick}")

            # Sending network messages
            # Send to the first player
            if player_socket in self.client_ciphers:
                player_cipher = self.client_ciphers[player_socket]
                enc_player_result = player_cipher.encrypt(player_result).hex()
                enc_player_score = player_cipher.encrypt(str(player_score)).hex()
                enc_opponent_score = player_cipher.encrypt(str(opponent_score)).hex()

                try:
                    player_protocol.send_msg("match_ended", enc_player_result, enc_player_score, enc_opponent_score)
                except Exception as e:
                    print(f"Could not send match_ended to {player_nick}: {e}")

            # Send to the opponent
            if opponent_socket in self.client_ciphers:
                opponent_cipher = self.client_ciphers[opponent_socket]
                enc_opponent_result = opponent_cipher.encrypt(opponent_result).hex()
                enc_opponent_score = opponent_cipher.encrypt(str(opponent_score)).hex()
                enc_player_score = opponent_cipher.encrypt(str(player_score)).hex()

                try:
                    opponent_protocol.send_msg("match_ended", enc_opponent_result, enc_opponent_score, enc_player_score)
                except Exception as e:
                    print(f"Could not send match_ended to opponent {opponent_nick}: {e}")

            # Remove match information for both players
            if player_socket in self.matches:
                del self.matches[player_socket]
            if opponent_socket in self.matches:
                del self.matches[opponent_socket]

            # Remove their current game scores
            if player_socket in self.game_scores:
                del self.game_scores[player_socket]
            if opponent_socket in self.game_scores:
                del self.game_scores[opponent_socket]

            print(f"Structures cleared for {player_nick} and {opponent_nick}. They can now play again.")

    def handle_logout(self, client_socket):
        if client_socket in self.connected_users:
            nickname = self.connected_users[client_socket]
            del self.connected_users[client_socket]
            print(f"{nickname} logged out")

    def handle_client(self, client_socket, address):
        print("Client connected:", address)
        protocol = Protocol(client_socket)

        # -----------------------------------------------------------------
        # KEY EXCHANGE STAGE (HANDSHAKE)
        # -----------------------------------------------------------------

        try:
            # Create an RSA handler object
            rsa_handler = RSAKeyExchange()

            # Generate an RSA key pair and get the public key
            server_public_key = rsa_handler.generate_keys()

            # Convert the public key to PEM text format
            public_pem = server_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')

            # Send the RSA public key to the client
            protocol.send_msg("public_key", public_pem)
            print(f"[Crypto]: Sent RSA public key to {address}")

            # Wait for the client's response
            msg_type, args = protocol.get_msg()

            # Verify that the client sent a session key
            if msg_type != "session_key":
                print(f"[Crypto Error]: Expected 'session_key', received '{msg_type}'. Connection terminated.")
                client_socket.close()
                return

            # Receive the encrypted symmetric key
            encrypted_symmetric_key = bytes.fromhex(args[0])

            # Decrypt it using the private RSA key
            decrypted_key = rsa_handler.decrypt_key(encrypted_symmetric_key)

            # Create a cipher for further communication with the client
            self.client_ciphers[client_socket] = SymmetricCipher(key=decrypted_key)

            # Handshake completed successfully
            print(f"[Crypto]: Symmetric key successfully established with {address}!")

        except Exception as crypto_err:
            # Handle cryptographic exchange errors
            print(f"[Crypto Error]: Handshake failed with {address}: {crypto_err}")
            client_socket.close()
            return

        # -----------------------------------------------------------------
        # MAIN REQUEST PROCESSING LOOP
        # -----------------------------------------------------------------

        try:
            while True:
                msg_type, args = protocol.get_msg()
                if not msg_type:
                    print("Client disconnected")
                    break

                cipher = self.client_ciphers[client_socket]

                try:
                    if msg_type == "signup":
                        nickname = cipher.decrypt(bytes.fromhex(args[0]))
                        password = cipher.decrypt(bytes.fromhex(args[1]))

                        MIN_NICK_LEN, MAX_NICK_LEN, MIN_PASSWORD_LEN = 3, 8, 8
                        SPECIAL_SYMBOLS = "!@#$%^&*()_-+="

                        has_upper = any(char.isupper() for char in password)
                        has_digit = any(char.isdigit() for char in password)
                        has_special = any(char in SPECIAL_SYMBOLS for char in password)

                        if len(nickname) < MIN_NICK_LEN:
                            enc_resp = cipher.encrypt("register_failed|Nickname too short").hex()
                            protocol.send_msg("too_short", enc_resp)
                            continue

                        if len(nickname) >= MAX_NICK_LEN:
                            enc_resp = cipher.encrypt("register_failed|Nickname too long").hex()
                            protocol.send_msg("too_long", enc_resp)
                            continue

                        if len(password) < MIN_PASSWORD_LEN or not has_upper or not has_digit or not has_special:
                            protocol.send_msg("password_error", "")
                            continue

                        if any(user["nickname"] == nickname for user in self.users):
                            enc_resp = cipher.encrypt("User already exists").hex()
                            protocol.send_msg("user_already_exists_error", enc_resp)
                        else:
                            password_hash, salt = DataHasher.hash_data(password)

                            new_user = {
                                "nickname": nickname,
                                "password_hash": password_hash.hex(),
                                "salt": salt.hex(),
                                "score": 0,
                                "opened_rounds": [],
                                "opened_tasks": [],
                                "solved_tasks": []
                            }
                            self.users.append(new_user)

                            with open(self.USERS_FILE, "w", encoding="utf-8") as f:
                                json.dump(self.users, f, ensure_ascii=False, indent=4)

                            self.connected_users[client_socket] = nickname

                            enc_user_data = cipher.encrypt(json.dumps(new_user)).hex()
                            protocol.send_msg("signup_success", enc_user_data)
                            print("Registration Secure Successful:", nickname)

                    elif msg_type == "login":
                        nickname = cipher.decrypt(bytes.fromhex(args[0]))
                        password = cipher.decrypt(bytes.fromhex(args[1]))

                        user = next((u for u in self.users if u["nickname"] == nickname), None)

                        if not user or "password_hash" not in user:
                            enc_resp = cipher.encrypt("Invalid username or password").hex()
                            protocol.send_msg("error_login", enc_resp)
                            continue

                        db_hash = bytes.fromhex(user["password_hash"])
                        db_salt = bytes.fromhex(user["salt"])

                        if not DataHasher.verify_data(password, db_hash, db_salt):
                            enc_resp = cipher.encrypt("Invalid username or password").hex()
                            protocol.send_msg("error_login", enc_resp)
                            continue

                        with self.lock:
                            if nickname in self.connected_users.values():
                                enc_resp = cipher.encrypt("login_failed|Account already online").hex()
                                protocol.send_msg("error_already_online", enc_resp)
                                continue
                            self.connected_users[client_socket] = nickname

                        enc_user_data = cipher.encrypt(json.dumps(user)).hex()
                        protocol.send_msg("success", enc_user_data)
                        print("User logged in securely:", nickname)

                    elif msg_type == "find_match":
                        player_nick = cipher.decrypt(bytes.fromhex(args[0]))
                        player_user = self.find_user(player_nick)

                        if player_user and len(player_user.get("opened_rounds", [])) >= 4:
                            enc_resp = cipher.encrypt("You have already played all rounds!").hex()
                            protocol.send_msg("you_played_all_games", enc_resp)
                            continue

                        with self.lock:
                            # Check whether this socket is already in the queue
                            if any(item[0] == client_socket for item in self.waiting_players):
                                continue

                            # If the player is already in an active match, do not queue again
                            if client_socket in self.matches and self.matches[client_socket].get("active"):
                                continue

                            if len(self.waiting_players) == 0:
                                self.waiting_players.append((client_socket, player_nick))
                                enc_resp = cipher.encrypt("Waiting for the second player").hex()
                                protocol.send_msg("wait", enc_resp)
                            else:
                                opponent_socket, opponent_nick = self.waiting_players.pop(0)
                                player_socket = client_socket

                                self.game_scores[player_socket] = 0
                                self.game_scores[opponent_socket] = 0

                                opponent_protocol = Protocol(opponent_socket)
                                player_protocol = Protocol(player_socket)
                                opp_cipher = self.client_ciphers[opponent_socket]

                                chosen_round, round_tasks = self.generate_match_round(player_nick, opponent_nick)

                                if chosen_round is None:
                                    enc_err_p = cipher.encrypt("No available rounds").hex()
                                    enc_err_o = opp_cipher.encrypt("No available rounds").hex()
                                    player_protocol.send_msg("error_rounds", enc_err_p)
                                    opponent_protocol.send_msg("error_rounds", enc_err_o)
                                    continue

                                player_user = self.find_user(player_nick)
                                opponent_user = self.find_user(opponent_nick)

                                for task in round_tasks:
                                    if task["id"] not in player_user["opened_tasks"]:
                                        player_user["opened_tasks"].append(task["id"])
                                    if task["id"] not in opponent_user["opened_tasks"]:
                                        opponent_user["opened_tasks"].append(task["id"])

                                self.save_user(player_user)
                                self.save_user(opponent_user)

                                match_start = time.time()

                                # Store match state for BOTH players
                                self.matches[player_socket] = {
                                    "opponent": opponent_socket,
                                    "round_id": chosen_round["id"],
                                    "round_tasks": chosen_round["tasks"],
                                    "active": True,
                                    "start_time": match_start
                                }

                                self.matches[opponent_socket] = {
                                    "opponent": player_socket,
                                    "round_id": chosen_round["id"],
                                    "round_tasks": chosen_round["tasks"],
                                    "active": True,
                                    "start_time": match_start
                                }

                                # Send data
                                game_data = {"round": chosen_round["name"], "tasks": round_tasks}
                                player_protocol.send_msg("game_tasks", cipher.encrypt(json.dumps(game_data)).hex())
                                opponent_protocol.send_msg("game_tasks",
                                                           opp_cipher.encrypt(json.dumps(game_data)).hex())

                                player_protocol.send_msg("start", cipher.encrypt(str(self.MATCH_TIME)).hex(),
                                                         cipher.encrypt(opponent_nick).hex())
                                opponent_protocol.send_msg("start", opp_cipher.encrypt(str(self.MATCH_TIME)).hex(),
                                                           opp_cipher.encrypt(player_nick).hex())

                                # Start timer
                                threading.Thread(target=self.match_timer, args=(player_socket,), daemon=True).start()

                    elif msg_type == "get_task_card":
                        nickname = self.connected_users.get(client_socket)
                        user = self.find_user(nickname)

                        tasks_preview = []
                        for task in self.tasks:
                            tasks_preview.append({
                                "id": task["id"], "title": task["title"], "difficulty": task["difficulty"],
                                "type": task["type"], "points": task["points"],
                                "reduced_points": task["reduced_points"],
                                "solves": task["solves"],
                            })

                        data = {
                            "tasks": tasks_preview,
                            "opened_tasks": user["opened_tasks"],
                            "solved_tasks": user["solved_tasks"]
                        }
                        protocol.send_msg("tasks_card", cipher.encrypt(json.dumps(data)).hex())

                    elif msg_type == "get_task_page":
                        task_id = int(cipher.decrypt(bytes.fromhex(args[0])))
                        nickname = self.connected_users.get(client_socket)
                        user = self.find_user(nickname)

                        if task_id in user["opened_tasks"]:
                            for task in self.tasks:
                                if task["id"] == task_id:
                                    task_page = {
                                        "id": task["id"], "title": task["title"], "difficulty": task["difficulty"],
                                        "type": task["type"], "points": task["points"],
                                        "reduced_points": task["reduced_points"],
                                        "solves": task["solves"], "description": task["description"],
                                        "files": task["files"]
                                    }
                                    protocol.send_msg("tasks_page_opened", cipher.encrypt(json.dumps(task_page)).hex())
                                    break
                        else:
                            protocol.send_msg("tasks_page_locked", cipher.encrypt(str(task_id)).hex())

                    elif msg_type == "score":
                        nickname = self.connected_users.get(client_socket)
                        user = self.find_user(nickname)
                        protocol.send_msg("your_score", cipher.encrypt(str(user["score"])).hex())

                    elif msg_type == "get_scoreboard":
                        with open(self.USERS_FILE, "r", encoding="utf-8") as f:
                            users_data = json.load(f)

                        users_sorted = sorted(users_data, key=lambda x: x["score"], reverse=True)
                        leaderboard = [{"nickname": u["nickname"], "score": u["score"]} for u in users_sorted[:100]]
                        protocol.send_msg("scoreboard", cipher.encrypt(json.dumps(leaderboard)).hex())

                    elif msg_type == "delete_account":
                        nickname = self.connected_users.get(client_socket)
                        if not nickname:
                            protocol.send_msg("error_delete", cipher.encrypt("Not logged in").hex())
                            continue

                        with open(self.USERS_FILE, "r", encoding="utf-8") as f:
                            self.users = json.load(f)

                        self.users = [u for u in self.users if u["nickname"] != nickname]

                        with open(self.USERS_FILE, "w", encoding="utf-8") as f:
                            json.dump(self.users, f, indent=4, ensure_ascii=False)

                        del self.connected_users[client_socket]

                    elif msg_type == "logout":
                        self.handle_logout(client_socket)

                    elif msg_type == "submit_library_flag":

                        # Decrypt the task ID and the user-submitted flag
                        task_id = int(cipher.decrypt(bytes.fromhex(args[0])))
                        user_flag = cipher.decrypt(bytes.fromhex(args[1]))

                        # Get information about the current user
                        nickname = self.connected_users.get(client_socket)
                        user = self.find_user(nickname)

                        # Find the task by its ID
                        task = next((t for t in self.tasks if t["id"] == task_id), None)
                        if not task:
                            return

                        # Verify the flag using hash and salt
                        is_flag_correct = DataHasher.verify_data(
                            user_flag,
                            bytes.fromhex(task["flag_hash"]),
                            bytes.fromhex(task["flag_salt"])
                        )

                        if is_flag_correct:

                            # Check whether the user has already solved this task
                            if task["id"] not in user["solved_tasks"]:

                                # Award points and mark the task as solved
                                user["score"] += task["reduced_points"]
                                user["solved_tasks"].append(task["id"])
                                task["solves"] += 1

                                # Notify the client about the successful solve
                                protocol.send_msg("task_completed", cipher.encrypt(str(task["id"])).hex())

                                # Save changes on the server
                                self.save_user(user)
                                self.save_tasks(self.tasks)

                                # Send the flag verification result
                                protocol.send_msg(
                                    "flag_result",
                                    cipher.encrypt("correct").hex(),
                                    cipher.encrypt(str(task["reduced_points"])).hex()
                                )

                                # Update local user data on the client
                                protocol.send_msg(
                                    "update_user",
                                    cipher.encrypt(json.dumps(user)).hex(),
                                    cipher.encrypt(str(task["id"])).hex()
                                )

                            else:
                                # The user has already solved this task
                                enc_status = cipher.encrypt("already_solved").hex()
                                enc_zero = cipher.encrypt("0").hex()
                                protocol.send_msg("flag_result", enc_status, enc_zero)

                        else:
                            # Send a message about an incorrect flag
                            enc_status = cipher.encrypt("wrong").hex()
                            enc_zero = cipher.encrypt("0").hex()
                            protocol.send_msg("flag_result", enc_status, enc_zero)


                    elif msg_type == "submit_game_flag":

                        # Get information about the current match
                        match = self.matches.get(client_socket)

                        # Verify that the match exists and is not finished
                        if not match or not match.get("active", True):
                            protocol.send_msg("flag_result", cipher.encrypt("wrong").hex(), "0")
                            continue

                        # Get the opponent's data and cipher
                        opponent_socket = match["opponent"]
                        opp_cipher = self.client_ciphers[opponent_socket]

                        # Decrypt the task ID and submitted flag
                        task_id = int(cipher.decrypt(bytes.fromhex(args[0])))
                        user_flag = cipher.decrypt(bytes.fromhex(args[1]))

                        # Get information about the player and task
                        nickname = self.connected_users.get(client_socket)
                        user = self.find_user(nickname)
                        task = next((t for t in self.tasks if t["id"] == task_id), None)

                        if not task:
                            continue

                        # Verify the flag
                        is_flag_correct = DataHasher.verify_data(
                            user_flag,
                            bytes.fromhex(task["flag_hash"]),
                            bytes.fromhex(task["flag_salt"])
                        )

                        if is_flag_correct:

                            # Check whether the task was solved before
                            if task["id"] not in user["solved_tasks"]:

                                # Award points and update task statistics
                                user["score"] += task["points"]
                                user["solved_tasks"].append(task["id"])
                                task["solves"] += 1

                                # Notify both players about the statistics update
                                protocol.send_msg("task_completed", cipher.encrypt(str(task["id"])).hex())

                                protocol.send_msg(
                                    "solves_update",
                                    cipher.encrypt(str(task["id"])).hex(),
                                    cipher.encrypt(str(task["solves"])).hex()
                                )

                                Protocol(opponent_socket).send_msg(
                                    "solves_update",
                                    opp_cipher.encrypt(str(task["id"])).hex(),
                                    opp_cipher.encrypt(str(task["solves"])).hex()
                                )

                                # Save changes
                                self.save_user(user)
                                self.save_tasks(self.tasks)

                                # Update the game score
                                self.game_scores[client_socket] = (
                                        self.game_scores.get(client_socket, 0) + task["points"]
                                )

                                # Send the verification result to the player
                                protocol.send_msg(
                                    "flag_result",
                                    cipher.encrypt("correct").hex(),
                                    cipher.encrypt(str(task["points"])).hex()
                                )

                                # Update the score on the client
                                protocol.send_msg(
                                    "your_score_update",
                                    cipher.encrypt(str(self.game_scores[client_socket])).hex()
                                )

                                # Update the opponent's score
                                if opponent_socket in self.matches:
                                    Protocol(opponent_socket).send_msg(
                                        "opponent_score_update",
                                        opp_cipher.encrypt(str(self.game_scores[client_socket])).hex()
                                    )

                                # Check the match completion condition
                                current_match = self.matches.get(client_socket)

                                if current_match:
                                    round_tasks = current_match["round_tasks"]

                                    if self.player_completed_round(user, round_tasks):
                                        self.finish_match(
                                            client_socket,
                                            winner_socket=client_socket
                                        )

                            else:
                                # The task has already been solved
                                enc_status = cipher.encrypt("already_solved").hex()
                                enc_zero = cipher.encrypt("0").hex()
                                protocol.send_msg("flag_result", enc_status, enc_zero)

                        else:
                            # Incorrect flag
                            enc_status = cipher.encrypt("wrong").hex()
                            enc_zero = cipher.encrypt("0").hex()
                            protocol.send_msg("flag_result", enc_status, enc_zero)

                        continue

                    elif msg_type == "get_history":
                        nickname = cipher.decrypt(bytes.fromhex(args[0]))
                        history = self.match_history.get(nickname, [])
                        protocol.send_msg("history", cipher.encrypt(json.dumps(history)).hex())

                except IndexError:
                    protocol.send_msg("error", "Invalid data")
                    print("Something went wrong: IndexError")

        except Exception as e:
            print(f"Exception in client thread: {e}")

        finally:
            print("CLIENT DISCONNECTED")

            # If the player was in a match, finish the game correctly
            if client_socket in self.matches:
                match_data = self.matches.get(client_socket)

                if match_data and isinstance(match_data, dict) and match_data.get("active", True):
                    opponent_socket = match_data.get("opponent")
                    print("Player disconnected during match. Finishing...")

                    # Victory is automatically awarded to the opponent
                    self.finish_match(player_socket=client_socket, winner_socket=opponent_socket)

                # Remove match information for both players
                opponent_socket = match_data.get("opponent") if isinstance(match_data, dict) else None

                if client_socket in self.matches:
                    del self.matches[client_socket]

                if opponent_socket and opponent_socket in self.matches:
                    del self.matches[opponent_socket]

            # Remove the user from active connections
            if client_socket in self.connected_users:
                nickname = self.connected_users[client_socket]
                del self.connected_users[client_socket]
                print(f"{nickname} disconnected")

            # Remove the client's session cipher
            if client_socket in self.client_ciphers:
                del self.client_ciphers[client_socket]

            # Close the network connection
            client_socket.close()

    def start(self):

        # Start the main socket listening loop

        print("Initializing server storage...")
        self.init_server_storage()

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server successfully started on {self.host}:{self.port}...")

        try:
            while True:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("\nServer shutting down gracefully...")
        finally:
            self.server_socket.close()


if __name__ == "__main__":

    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 5555
    server = Server(host=SERVER_HOST, port=SERVER_PORT)
    server.start()