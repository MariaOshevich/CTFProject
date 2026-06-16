"""
Client Module

This module is responsible for handling the client-side logic of the system.
It manages the connection to the server, sends requests, receives responses,
and processes incoming data according to the defined communication protocol.
"""

# =========================================================
# IMPORTS
# =========================================================

import socket
import threading
import shutil
import os
import json
import webbrowser

from tkinter import *
from PIL import Image, ImageTk

# PROTOCOL MODULE
from Protocol import Protocol

# SECURITY MODULE
from Security import RSAKeyExchange, SymmetricCipher
from cryptography.hazmat.primitives import serialization


# =========================================================
# MAIN CLIENT CLASS (OOP)
# =========================================================

class Client:
    def __init__(self, root, host="127.0.0.1", port=5555):
        # Tkinter window initialization
        self.root = root

        # Network configuration
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Application state
        self.game_active = False
        self.current_user = None
        self.user_flags = {}
        self.current_nickname = None
        self.current_opponent = ""
        self.player_mode = "library"
        self.your_game_score = 0
        self.opponent_game_score = 0
        self.seconds = 30
        self.task_cards = []

        # Session cipher
        self.cipher = None
        self.running = True

        # Server connection and protocol initialization
        self.socket.connect((self.host, self.port))
        self.protocol = Protocol(self.socket)

        # References to UI elements (initialized later)
        self.main_menu_frame = None
        self.menu_frame = None
        self.game_frame = None
        self.waiting_room_frame = None
        self.end_of_game_frame = None
        self.profile_window = None
        self.are_you_sure_frame = None
        self.result_frame = None

        self.menu_title_label = None
        self.game_opponent = None
        self.timer = None
        self.game_score_label = None
        self.opponent_score_label = None
        self.who_won_label = None
        self.score_label = None
        self.score = None
        self.result_label = None

        # Input fields (login/sign-up)
        self.nickname_signup_entry = None
        self.password_signup_entry = None
        self.nickname_login_entry = None
        self.password_login_entry = None

        # Error messages
        self.too_short_label = None
        self.too_long_label = None
        self.error_label3 = None
        self.password_error_label1 = None
        self.password_error_label2 = None
        self.error_label_already_online = None
        self.error_label_wrong_password_or_nickname = None
        self.you_played_all_games_label = None
        self.challenges_content = None
        self.scoreboard_content = None
        self.history_content = None

        # Start background server listener thread
        threading.Thread(target=self.listen_server, daemon=True).start()

    def send(self, *args):
        # Send messages through the custom protocol
        self.protocol.send_msg(*args)

    def listen_server(self):

        # Main server response listener

        # -------------------------------------------------------------
        # [SECURITY] HANDSHAKE STAGE
        # -------------------------------------------------------------

        try:
            msg_type, args = self.protocol.get_msg()
            if msg_type != "public_key":
                print("[CryptoError] Expected public_key from server. Connection terminated.")
                self.running = False
                return

            server_public_pem = args[0].encode('utf-8')
            server_public_key = serialization.load_pem_public_key(server_public_pem)

            # Create a unique symmetric cipher for this client session
            self.cipher = SymmetricCipher()

            rsa_exchange = RSAKeyExchange()
            encrypted_session_key = rsa_exchange.encrypt_key(server_public_key, self.cipher.key)

            self.protocol.send_msg("session_key", encrypted_session_key.hex())
            print("[Крипто] Handshake completed successfully. Traffic is protected!")

        except Exception as crypto_err:
            print(f"[CryptoError] Failed to negotiate keys: {crypto_err}")
            self.running = False
            return

        # -------------------------------------------------------------
        # MAIN SERVER COMMAND PROCESSING LOOP
        # -------------------------------------------------------------

        while self.running:
            msg_type, args = self.protocol.get_msg()

            if not msg_type:
                break

            print("DEBUG (Raw/Encrypted):", msg_type, args)

            if msg_type == "success":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_success(decrypted_args)

            elif msg_type == "signup_success":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_registration_success(decrypted_args)

            elif msg_type == "error_login":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_error_login(decrypted_args)

            elif msg_type == "error_already_online":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_error_already_online(decrypted_args)

            elif msg_type == "too_short":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_too_short(decrypted_args)

            elif msg_type == "too_long":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_too_long(decrypted_args)

            elif msg_type == "user_already_exists_error":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_user_already_exists_error(decrypted_args)

            elif msg_type == "password_error":
                self.hangle_wrong_password(args)

            elif msg_type == "tasks_card":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_task_card(decrypted_args)

            elif msg_type == "tasks_page_opened":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_task_page_opened(decrypted_args)

            elif msg_type == "tasks_page_locked":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_task_data_locked(decrypted_args)

            elif msg_type == "your_score":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_score(decrypted_args)

            elif msg_type == "wait":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_waiting(decrypted_args)

            elif msg_type == "start":
                self.game_active = True

                decrypted_time = self.cipher.decrypt(bytes.fromhex(args[0]))
                decrypted_opp = self.cipher.decrypt(bytes.fromhex(args[1]))

                match_time = int(decrypted_time)
                self.current_opponent = decrypted_opp

                if self.game_opponent:
                    self.game_opponent.config(text=f"Your opponent: {self.current_opponent}")

                self.reset_game(match_time)
                self.show_frame(self.game_frame)
                self.update_timer()

                self.player_mode = "game"

                self.send("get_task_card")
                self.send("score")
                self.send("get_scoreboard")

            elif msg_type == "you_played_all_games":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_you_played_all_games(decrypted_args)

            elif msg_type == "scoreboard":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_scoreboard(decrypted_args)

            elif msg_type == "history":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_history(decrypted_args)

            elif msg_type == "game_tasks":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_game_tasks(decrypted_args)

            elif msg_type == "flag_result":
                decrypted_res = self.cipher.decrypt(bytes.fromhex(args[0]))
                decrypted_pts = self.cipher.decrypt(bytes.fromhex(args[1]))
                self.handle_flag_result([decrypted_res, decrypted_pts])

            elif msg_type == "opponent_score_update":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_opponent_score(decrypted_args)

            elif msg_type == "your_score_update":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_your_score(decrypted_args)

            elif msg_type == "match_ended":
                decrypted_res = self.cipher.decrypt(bytes.fromhex(args[0]))
                decrypted_my = self.cipher.decrypt(bytes.fromhex(args[1]))
                decrypted_en = self.cipher.decrypt(bytes.fromhex(args[2]))
                self.handle_match_ended([decrypted_res, decrypted_my, decrypted_en])

            elif msg_type == "solves_update":
                decrypted_tid = self.cipher.decrypt(bytes.fromhex(args[0]))
                decrypted_slv = self.cipher.decrypt(bytes.fromhex(args[1]))
                self.handle_solves_update([decrypted_tid, decrypted_slv])

            elif msg_type == "task_completed":
                decrypted_args = [self.cipher.decrypt(bytes.fromhex(args[0]))]
                self.handle_task_completed(decrypted_args)

            elif msg_type == "update_user":
                decrypted_usr = self.cipher.decrypt(bytes.fromhex(args[0]))
                decrypted_tid = self.cipher.decrypt(bytes.fromhex(args[1]))
                self.handle_update_user([decrypted_usr, decrypted_tid])

    # =========================================================
    # UI HELPERS (METHODS)
    # =========================================================

    def show_frame(self, frame):
        self.close_all_overlays()
        if frame:
            frame.tkraise()

    def send_signup(self):
        nickname = self.nickname_signup_entry.get()
        password = self.password_signup_entry.get()

        enc_nick = self.cipher.encrypt(nickname).hex()
        enc_pass = self.cipher.encrypt(password).hex()
        self.protocol.send_msg("signup", enc_nick, enc_pass)

    def send_login(self):
        nickname = self.nickname_login_entry.get()
        password = self.password_login_entry.get()

        enc_nick = self.cipher.encrypt(nickname).hex()
        enc_pass = self.cipher.encrypt(password).hex()
        self.protocol.send_msg("login", enc_nick, enc_pass)

    def find_match(self):
        nickname = self.nickname_login_entry.get()
        enc_nick = self.cipher.encrypt(nickname).hex()
        self.protocol.send_msg("find_match", enc_nick)

    def delete_account(self):
        self.protocol.send_msg("delete_account")
        self.logout()

    def update_timer(self):
        if not self.game_active:
            return
        minutes = self.seconds // 60
        sec = self.seconds % 60
        if self.timer:
            self.timer.config(text=f"{minutes}:{sec:02}")
        if self.seconds <= 0:
            if self.timer:
                self.timer.config(text="0:00")
            return
        self.seconds -= 1
        if self.game_frame:
            self.game_frame.after(1000, self.update_timer)

    def create_scrollable_frame(self, parent, bg_color):
        container = Frame(parent, bg=bg_color)
        container.pack(fill="both", expand=True)

        canvas = Canvas(container, bg=bg_color, highlightthickness=0)
        scrollbar = Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollable_frame = Frame(canvas, bg=bg_color)
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def update_scrollregion(event=None):
            canvas.update_idletasks()
            canvas.configure(
                scrollregion=(0, 0, scrollable_frame.winfo_reqwidth(), scrollable_frame.winfo_reqheight() + 100))

        scrollable_frame.bind("<Configure>", update_scrollregion)

        def resize_frame(event):
            canvas.itemconfig(window_id, width=event.width)

        canvas.bind("<Configure>", resize_frame)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return scrollable_frame

    def toggle_profile(self):
        if self.profile_window.winfo_ismapped():
            self.profile_window.place_forget()
            self.are_you_sure_frame.place_forget()
        else:
            nickname = self.current_nickname
            self.profile_title.config(text=f"Welcome, {nickname}")
            self.profile_window.place(relx=0.85, rely=0.5, anchor=CENTER)

    def toggle_tools_window(self):
        if self.tools_frame.winfo_viewable():
            if self.ascii_label:
                self.ascii_label.place_forget()
            self.tools_frame.place_forget()
        else:
            self.tools_frame.place(relx=0.8, rely=0.7, anchor="w")
            self.tools_frame.lift()

    def toggle_ascii_image(self):
        if self.ascii_label and self.ascii_label.winfo_viewable():
            self.ascii_label.place_forget()
            return

        if self.ascii_label:
            self.ascii_label.place(relx=0.6, rely=0.7, anchor=CENTER)
            return

        # On first click, load the image from file
        try:
            pil_img = Image.open("pictures/ASCII.png")
            width_size = 450
            w_percent = (width_size / float(pil_img.size[0]))
            h_size = int((float(pil_img.size[1]) * float(w_percent)))
            pil_img = pil_img.resize((width_size, h_size), Image.Resampling.LANCZOS)

            self.ascii_tk_image = ImageTk.PhotoImage(pil_img)

            # Create an image Label inside tools_frame
            self.ascii_label = Label(self.root, image=self.ascii_tk_image, bg="#2f2f2f")
            self.ascii_label.place(relx=0.6, rely=0.7, anchor=CENTER)
        except FileNotFoundError:
            print("Error: Could not find image file for ASCII table")
        except Exception as e:
            print(f"Image loading error: {e}")

    def close_all_overlays(self):
        # Hide all popups, tool panels, and profiles
        if hasattr(self, 'tools_frame'):
            self.tools_frame.place_forget()
        if hasattr(self, 'profile_window'):
            self.profile_window.place_forget()
        if hasattr(self, 'ascii_label') and self.ascii_label:
            self.ascii_label.place_forget()
        if hasattr(self, 'are_you_sure_frame'):
            self.are_you_sure_frame.place_forget()

    def logout(self):
        self.protocol.send_msg("logout")
        self.current_nickname = None

        if self.profile_window: self.profile_window.place_forget()
        if self.are_you_sure_frame: self.are_you_sure_frame.place_forget()

        if self.nickname_login_entry: self.nickname_login_entry.delete(0, END)
        if self.password_login_entry: self.password_login_entry.delete(0, END)
        if self.nickname_signup_entry: self.nickname_signup_entry.delete(0, END)
        if self.password_signup_entry: self.password_signup_entry.delete(0, END)

        self.show_frame(self.log_in_frame)

    def are_you_sure(self):
        if self.are_you_sure_frame:
            self.are_you_sure_frame.place(relx=0.5, rely=0.5, anchor=CENTER)

    def show_game_tasks(self, tasks):
        for card in self.task_cards:
            card.frame.destroy()
        self.task_cards.clear()

        Frame(self.game_frame, height=50, bg=self.game_frame["bg"]).grid(row=0, column=0)

        for i, task in enumerate(tasks):

            card = TaskCard(
                app=self,
                parent=self.game_frame,
                info=task,
                row=i + 1,
                column=0,
                is_opened=True,
                mode="game"
            )
            self.task_cards.append(card)

    def reset_game(self, match_time):
        self.your_game_score = 0
        self.opponent_game_score = 0
        self.seconds = match_time

        if self.game_score_label:
            self.game_score_label.config(text=f"Your score: {self.your_game_score}")
        if self.opponent_score_label:
            self.opponent_score_label.config(text=f"Opponent's score: {self.opponent_game_score}")

    def end_game(self, my_score, opponent_score):
        self.show_frame(self.end_of_game_frame)

        if my_score > opponent_score:
            result_text = "YOU WIN!"
        elif my_score < opponent_score:
            result_text = "YOU LOSE!"
        else:
            result_text = "DRAW!"

        if self.who_won_label: self.who_won_label.config(text=result_text)
        if self.score_label: self.score_label.config(text=f"You: {my_score} | Opponent: {opponent_score}")
        self.protocol.send_msg("game_over")


    # =========================================================
    # HANDLERS AS METHODS
    # =========================================================

    def handle_task_completed(self, args):
        task_id = int(args[0])
        self.current_user["solved_tasks"].append(task_id)

        for card in self.task_cards:
            if card.info["id"] == task_id:
                card.status_label.config(text="Completed", fg="green")

    def handle_update_user(self, args):
        self.current_user = json.loads(args[0])
        task_id = int(args[1])

        # Store the flag that was just sent to the server
        self.user_flags[task_id] = getattr(self, "app.last_submitted_flag", "hidden")

    def handle_solves_update(self, args):
        task_id = int(args[0])
        solves = int(args[1])

        for task in self.task_cards:
            if task.info["id"] == task_id:
                task.info["solves"] = solves
                task.solves.config(text=f"{solves} solves")

    def enter_main_menu(self, nickname=None):
        self.show_frame(self.main_menu_frame)
        self.show_frame(self.menu_frame)

        if nickname is None:
            nickname = self.nickname_login_entry.get()

        if self.menu_title_label:
            self.menu_title_label.config(text=f"Welcome, {nickname}")

        self.protocol.send_msg("get_task_card")
        self.protocol.send_msg("score")
        self.protocol.send_msg("get_scoreboard")

        enc_nick = self.cipher.encrypt(self.current_nickname).hex()
        self.protocol.send_msg("get_history", enc_nick)

    def handle_success(self, args):
        self.current_nickname = self.nickname_login_entry.get()
        self.enter_main_menu(self.current_nickname)
        self.current_user = json.loads(args[0])
        print("User loaded:", self.current_user)

    def handle_registration_success(self, args):
        self.current_nickname = self.nickname_signup_entry.get()
        self.enter_main_menu(self.current_nickname)
        self.current_user = json.loads(args[0])
        print("User signed up:", self.current_user)

    def hide_errors(self):
        if self.too_short_label: self.too_short_label.place_forget()
        if self.too_long_label: self.too_long_label.place_forget()
        if self.error_label3: self.error_label3.place_forget()

    def handle_error_already_online(self, args):
        if self.error_label_already_online:
            self.error_label_already_online.place(relx=0.4, y=500)

    def handle_error_login(self, args):
        if self.error_label_wrong_password_or_nickname:
            self.error_label_wrong_password_or_nickname.place(relx=0.4, y=500)

    def handle_too_short(self, args):
        self.hide_errors()
        if self.too_short_label: self.too_short_label.place(relx=0.4, y=615)

    def handle_too_long(self, args):
        self.hide_errors()
        if self.too_long_label: self.too_long_label.place(relx=0.4, y=615)

    def handle_user_already_exists_error(self, args):
        self.hide_errors()
        if self.password_error_label1: self.password_error_label1.place(relx=0.4, y=615)

    def hangle_wrong_password(self, args):
        self.hide_errors()
        if self.password_error_label2: self.password_error_label2.place(relx=0.4, y=615)

    def handle_waiting(self, args):
        self.show_frame(self.waiting_room_frame)

    def handle_task_card(self, args):
        try:
            data = json.loads(args[0])
            tasks = data["tasks"]
            opened_tasks = data["opened_tasks"]
            solved_tasks = data["solved_tasks"]

            if self.challenges_content:
                # Clear widgets
                self.root.after(0, self._clear_challenges)

            # Pass task card creation to the main thread
            self.root.after(0, self._render_task_cards, tasks, opened_tasks, solved_tasks)

        except Exception as e:
            print(f"[handle_task_card error]: {e}. Check the structure of the received JSON.")

    def _clear_challenges(self):
        # Helper cleanup method
        if self.challenges_content:
            for widget in self.challenges_content.winfo_children():
                widget.destroy()

    def _render_task_cards(self, tasks, opened_tasks, solved_tasks):

        for i, task in enumerate(tasks):
            r = i // 2
            c = i % 2

            is_opened = task["id"] in opened_tasks

            TaskCard(self, self.challenges_content, task, r, c + 1, is_opened, mode="library")

    def handle_task_page_opened(self, args):
        task_data = json.loads(args[0])
        print("Task is opened:", task_data["title"])
        TaskPage(self, task_data, self.player_mode)

    def handle_task_data_locked(self, args):
        task_id = args[0]
        print(f"Task {task_id} is closed")

    def handle_score(self, args):
        if self.score:
            self.score.config(text=f"Your total score: {args[0]}")

    def handle_scoreboard(self, args):
        if not self.scoreboard_content: return

        players_list = json.loads(args[0])

        title = Label(self.scoreboard_content, text="TOP PLAYERS", font=("Arial", 24, "bold"), fg="white", bg="black")
        title.grid(row=2, column=0, columnspan=3, pady=10)

        scoreboard_background = Frame(self.scoreboard_content, bg="#2f2f2f", borderwidth=2, relief="solid",
                                      highlightbackground="#999999", highlightthickness=1)
        scoreboard_background.grid(row=4, column=0, columnspan=3)
        scoreboard_background.config(width=500, height=50)
        scoreboard_background.grid_propagate(False)

        Label(scoreboard_background, text="Rank", fg="white", bg="#2f2f2f", font=("Consolas", 20, "bold")).place(
            relx=0.1, rely=0.5, anchor=CENTER)
        Label(scoreboard_background, text="Nickname", fg="white", bg="#2f2f2f", font=("Consolas", 20, "bold")).place(
            relx=0.5, rely=0.5, anchor=CENTER)
        Label(scoreboard_background, text="Score", fg="white", bg="#2f2f2f", font=("Consolas", 20, "bold")).place(
            relx=0.9, rely=0.5, anchor=CENTER)

        for i, player in enumerate(players_list, start=1):
            bg_fr = Frame(self.scoreboard_content, bg="#2f2f2f", borderwidth=2, relief="solid",
                          highlightbackground="#999999", highlightthickness=1)
            bg_fr.grid(row=i + 4, column=0, columnspan=3)
            bg_fr.config(width=500, height=50)
            bg_fr.grid_propagate(False)

            Label(bg_fr, text=str(i), fg="white", bg="#2f2f2f", font=("Consolas", 20)).place(relx=0.034, rely=0.5,
                                                                                             anchor="w")
            Label(bg_fr, text=player['nickname'], fg="white", bg="#2f2f2f", font=("Consolas", 20)).place(relx=0.3735,
                                                                                                         rely=0.5,
                                                                                                         anchor="w")
            Label(bg_fr, text=player['score'], fg="white", bg="#2f2f2f", font=("Consolas", 20)).place(relx=0.82,
                                                                                                      rely=0.5,
                                                                                                      anchor="w")

        self.scoreboard_content.grid_anchor("center")

    def handle_history(self, args):
        if not self.history_content: return

        for widget in self.history_content.winfo_children():
            widget.destroy()

        history = json.loads(args[0])
        history = list(reversed(history))

        title = Label(self.history_content, text="HISTORY", font=("Arial", 24, "bold"), fg="white", bg="black")
        title.grid(row=0, column=0, columnspan=3, pady=10)

        for i, match in enumerate(history, start=1):
            frame = Frame(self.history_content, bg="#2f2f2f", borderwidth=2, relief="solid",
                          highlightbackground="#999999", highlightthickness=1)
            frame.grid(row=i, column=0, columnspan=3, pady=10)
            frame.config(width=700, height=130)
            frame.grid_propagate(False)

            Label(frame, text=f"Your opponent: {match['opponent']}", fg="white", bg="#2f2f2f",
                  font=("Consolas", 18, "bold")).place(relx=0.05, rely=0.35, anchor="w")
            Label(frame, text=f"Winner: {match['winner']}", fg="white", bg="#2f2f2f",
                  font=("Consolas", 18, "bold")).place(relx=0.05, rely=0.65, anchor="w")

            match_time = match["time"]
            minutes = match_time // 60
            seconds_val = match_time % 60

            Label(frame, text=f"Time: {minutes}:{seconds_val:02}", fg="white", bg="#2f2f2f",
                  font=("Consolas", 18, "bold")).place(relx=0.55, rely=0.25, anchor="w")
            Label(frame, text=f"Your score: {match['my_score']}", fg="white", bg="#2f2f2f",
                  font=("Consolas", 18, "bold")).place(relx=0.55, rely=0.5, anchor="w")
            Label(frame, text=f"Opponent's score: {match['enemy_score']}", fg="white", bg="#2f2f2f",
                  font=("Consolas", 18, "bold")).place(relx=0.55, rely=0.75, anchor="w")

        self.history_content.grid_anchor("center")

    def handle_game_tasks(self, args):
        data = json.loads(args[0])
        round_name = data["round"]
        tasks = data["tasks"]

        print("ROUND:", round_name)
        self.show_game_tasks(tasks)

    def handle_flag_result(self, args):
        result = args[0]
        points = int(args[1])

        if result == "correct":
            print("Correct flag!")
            if self.player_mode == "game" and self.game_score_label:
                self.game_score_label.config(text=f"Your score: {self.your_game_score}")

            if self.result_label:
                self.result_label.config(text=f"Correct flag!, you've earned {points} points", fg="green")

            self.send("score")
            self.send("get_scoreboard")
            self.send("get_task_card")

        elif result == "already_solved":
            print("Already solved!")
            if self.result_label: self.result_label.config(text="This task is already solved!", fg="red")
        else:
            print("Wrong flag!")
            if self.result_label: self.result_label.config(text="Wrong flag!", fg="red")

        if self.result_frame:
            self.result_frame.place(relx=0.5, rely=0.5, anchor=CENTER)
            self.result_frame.lift()
            self.result_frame.after(2000, self.result_frame.place_forget)

    def handle_opponent_score(self, args):
        self.opponent_game_score = int(args[0])
        if self.game_frame and self.game_frame.winfo_ismapped() and self.opponent_score_label:
            self.opponent_score_label.config(text=f"Opponent's score: {self.opponent_game_score}")

    def handle_your_score(self, args):
        self.your_game_score = int(args[0])
        if self.game_score_label:
            self.game_score_label.config(text=f"Your score: {self.your_game_score}")

    def handle_match_ended(self, args):
        self.close_all_overlays()
        self.game_active = False
        self.player_mode = "library"

        result = args[0]
        my_score = args[1]
        opponent_score = args[2]

        print("Match ended:", result)
        self.show_frame(self.end_of_game_frame)

        if result == "win":
            if self.who_won_label: self.who_won_label.config(text="YOU WIN!")
        elif result == "lose":
            if self.who_won_label: self.who_won_label.config(text="YOU LOSE!")
        else:
            if self.who_won_label: self.who_won_label.config(text="DRAW!")

        if self.score_label:
            self.score_label.config(text=f"You: {my_score} | Opponent: {opponent_score}")

        enc_nick = self.cipher.encrypt(self.current_nickname).hex()
        self.send("get_history", enc_nick)
        self.send("get_task_card")
        self.send("score")

    def handle_you_played_all_games(self, args):
        if self.you_played_all_games_label:
            self.you_played_all_games_label.place(relx=0.5, rely=0.5, anchor=CENTER, width=550, height=250)
            self.you_played_all_games_label.lift()
            self.you_played_all_games_label.after(2000, self.you_played_all_games_label.place_forget)

    def build_ui(self):
        container = Frame(self.root)
        container.place(x=0, y=0, relwidth=1, relheight=1)

        # Application frame containers
        self.log_in_frame = Frame(container, bg="black")
        self.sign_up_frame = Frame(container, bg="black")
        self.main_menu_frame = Frame(container, bg="#d16676")
        self.waiting_room_frame = Frame(container, bg="black")

        self.game_frame = Frame(container, bg="black")
        self.game_frame.columnconfigure(0, weight=1)
        self.game_frame.grid_propagate(False)

        self.end_of_game_frame = Frame(container, bg="black")

        for f in (self.log_in_frame, self.sign_up_frame, self.main_menu_frame, self.waiting_room_frame, self.game_frame,
                  self.end_of_game_frame):
            f.place(x=0, y=0, relwidth=1, relheight=1)

        # LOGIN FRAME SECTION

        title = Label(self.log_in_frame, text="Capture The Flag", fg="white", bg="#2f2f2f",
                      font=("Consolas", 36, "bold"))
        title.place(relx=0.5, y=100, anchor=CENTER)

        Label(self.log_in_frame, text="Log in", fg="white", bg="#2f2f2f", font=("Consolas", 24)).place(relx=0.5, y=200,
                                                                                                       anchor=CENTER)
        Label(self.log_in_frame, text="Nickname", fg="white", bg="#2f2f2f", font=("Consolas", 14)).place(relx=0.4,
                                                                                                         y=260)

        self.nickname_login_entry = Entry(self.log_in_frame, font=("Consolas", 14), width=30)
        self.nickname_login_entry.place(relx=0.4, y=290)

        Label(self.log_in_frame, text="Password", fg="white", bg="#2f2f2f", font=("Consolas", 14)).place(relx=0.4,
                                                                                                         y=340)

        self.password_login_entry = Entry(self.log_in_frame, font=("Consolas", 14), width=30, show="*")
        self.password_login_entry.place(relx=0.4, y=370)

        log_in_button = Button(self.log_in_frame, text="Log in", fg="white", bg="#2f2f2f", font=("Consolas", 14),
                               command=self.send_login)
        log_in_button.place(relx=0.4, y=430)

        sign_up_link = Label(self.log_in_frame, text="Don't have an account? Click here", fg="red",
                             font=("Consolas", 14), cursor="hand2")
        sign_up_link.place(relx=0.4, y=580)
        sign_up_link.bind("<Button-1>", lambda e: self.show_frame(self.sign_up_frame))

        self.error_label_wrong_password_or_nickname = Label(self.log_in_frame, text="Nickname or password are wrong",
                                                            fg="red", bg=self.log_in_frame["bg"], font=("Consolas", 12))
        self.error_label_already_online = Label(self.log_in_frame, text="login_failed|Account already online", fg="red",
                                                bg=self.log_in_frame["bg"], font=("Consolas", 12))

        # SIGN UP FRAME SECTION


        title1 = Label(self.sign_up_frame, text="Capture The Flag", fg="white", bg="#2f2f2f",
                       font=("Consolas", 36, "bold"))
        title1.place(relx=0.5, y=100, anchor=CENTER)

        Label(self.sign_up_frame, text="Sign up", fg="white", bg="#2f2f2f", font=("Consolas", 24)).place(relx=0.5,
                                                                                                         y=200,
                                                                                                         anchor=CENTER)
        Label(self.sign_up_frame, text="Nickname", fg="white", bg="#2f2f2f", font=("Consolas", 14)).place(relx=0.4,
                                                                                                          y=260)

        self.nickname_signup_entry = Entry(self.sign_up_frame, font=("Consolas", 14), width=30)
        self.nickname_signup_entry.place(relx=0.4, y=290)

        Label(self.sign_up_frame, text="Password", fg="white", bg="#2f2f2f", font=("Consolas", 14)).place(relx=0.4,
                                                                                                          y=340)

        self.password_signup_entry = Entry(self.sign_up_frame, font=("Consolas", 14), width=30, show="*")
        self.password_signup_entry.place(relx=0.4, y=370)

        password_conditions = Label(self.sign_up_frame, text="The password must meet the following requirements:\n"
                                                             "- Contain at least 8 characters\n"
                                                             "- Include at least one uppercase letter\n"
                                                             "- Include at least one digit\n"
                                                             "- Contain at least one special character from the following list:\n"
                                                             "  ! @ # $ % ^ & * ( ) _ - + =", justify="left",
                                    anchor="w", fg="white", bg=self.log_in_frame["bg"], font=("Consolas", 12))
        password_conditions.place(relx=0.4, y=420)

        sign_up_button = Button(self.sign_up_frame, text="Sign up", fg="white", bg="#2f2f2f", font=("Consolas", 14),
                                command=self.send_signup)
        sign_up_button.place(relx=0.4, y=560)

        sign_back_link = Label(self.sign_up_frame, text="Go back to the Log in page", fg="red", font=("Consolas", 14),
                               cursor="hand2")
        sign_back_link.place(relx=0.4, y=670)
        sign_back_link.bind("<Button-1>", lambda e: self.show_frame(self.log_in_frame))

        self.error_label3 = Label(self.sign_up_frame, text="This nickname is already taken", fg="red",
                                  bg=self.log_in_frame["bg"], font=("Consolas", 12))
        self.too_short_label = Label(self.sign_up_frame, text="Your nickname is too short", fg="red",
                                     bg=self.log_in_frame["bg"], font=("Consolas", 12))
        self.too_long_label = Label(self.sign_up_frame, text="Your nickname is too long", fg="red",
                                    bg=self.log_in_frame["bg"], font=("Consolas", 12))

        self.password_error_label1 = Label(self.sign_up_frame, text="This nickname is already taken", fg="red",
                                           bg=self.log_in_frame["bg"], font=("Consolas", 12))
        self.password_error_label2 = Label(self.sign_up_frame, text="Password does not meet the requirements", fg="red",
                                           bg=self.log_in_frame["bg"], font=("Consolas", 12))

        # MAIN MENU FRAME SECTION


        self.main_menu_frame.place(x=0, y=100, relwidth=1, relheight=1, anchor="nw")

        self.menu_frame = Frame(container, bg="#0f172a", height=100, width=1600)
        self.menu_frame.place(x=0, y=0, relwidth=1)

        self.menu_title_label = Label(self.menu_frame, fg="white", bg="#0f172a", font=("Consolas", 24, "bold"))
        self.menu_title_label.place(relx=0.1, rely=0.5, anchor=CENTER)

        # MENU FRAMES

        Profile = Frame(self.main_menu_frame, bg="black")
        About = Frame(self.main_menu_frame, bg="red")
        Learn = Frame(self.main_menu_frame, bg="blue")
        Challenges = Frame(self.main_menu_frame, bg="green")
        Scoreboard = Frame(self.main_menu_frame, bg="yellow")
        History = Frame(self.main_menu_frame, bg="red")
        Start = Frame(self.main_menu_frame, bg="purple")

        for frame in (About, Learn, Challenges, Scoreboard, Profile, Start, History):
            frame.place(x=0, y=0, relwidth=1, relheight=1)


        # SCROLL CONTENT


        self.profile_content = self.create_scrollable_frame(Profile, "black")
        about_content = self.create_scrollable_frame(About, "black")
        learn_content = self.create_scrollable_frame(Learn, "black")
        self.challenges_content = self.create_scrollable_frame(Challenges, "black")
        self.scoreboard_content = self.create_scrollable_frame(Scoreboard, "black")
        self.history_content = self.create_scrollable_frame(History, "black")
        start_content = self.create_scrollable_frame(Start, "black")

        # Top navigation menu buttons
        Button(self.menu_frame, text="About", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a",
               command=lambda: self.show_frame(About)).place(relx=0.35, y=50, anchor=CENTER)
        Button(self.menu_frame, text="Learn", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a",
               command=lambda: self.show_frame(Learn)).place(relx=0.45, y=50, anchor=CENTER)
        Button(self.menu_frame, text="Challenges", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a",
               command=lambda: self.show_frame(Challenges)).place(relx=0.55, y=50, anchor=CENTER)
        Button(self.menu_frame, text="Scoreboard", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a",
               command=lambda: self.show_frame(Scoreboard)).place(relx=0.65, y=50, anchor=CENTER)
        Button(self.menu_frame, text="History", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a",
               command=lambda: self.show_frame(History)).place(relx=0.75, y=50, anchor=CENTER)
        Button(self.menu_frame, text="Profile", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a",
               command=lambda: self.toggle_profile()).place(relx=0.9, y=50, anchor=CENTER)
        Button(self.menu_frame, text="Start", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a",
               command=lambda: self.show_frame(Start)).place(relx=0.25, y=50, anchor=CENTER)

        # PROFILE SECTION

        self.profile_window = Frame(self.root, bg="#2f2f2f", width=400, height=500)
        self.profile_title = Label(self.profile_window, fg="white", bg="#2f2f2f", font=("Consolas", 24, "bold"))
        self.profile_title.place(relx=0.5, rely=0.15, anchor=CENTER)

        Button(self.profile_window, text="Log out", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#2f2f2f",
               command=lambda: self.logout()).place(relx=0.5, rely=0.5, anchor=CENTER)
        Button(self.profile_window, text="Delete account", width=18, font=("Consolas", 15, "bold"), fg="white",
               bg="red", command=lambda: self.are_you_sure()).place(relx=0.5, rely=0.65, anchor=CENTER)

        self.are_you_sure_frame = Frame(self.root, bg="#0f172a", width=900, height=200)
        Label(self.are_you_sure_frame, text="Are you sure you want to delete this account?", bg="#0f172a", fg="white",
              font=("Consolas", 20, "bold")).place(relx=0.5, rely=0.3, anchor=CENTER)

        Button(self.are_you_sure_frame, text="Delete account", width=18, font=("Consolas", 15, "bold"), fg="white",
               bg="red", command=lambda: self.delete_account()).place(relx=0.4, rely=0.6, anchor=CENTER)
        Button(self.are_you_sure_frame, text="Cancel", width=12, font=("Consolas", 15, "bold"), fg="white",
               bg="#0f172a", command=lambda: self.are_you_sure_frame.place_forget()).place(relx=0.6, rely=0.6,
                                                                                           anchor=CENTER)

        # START SECTION

        start_button = Button(start_content, text="Start", fg="white", bg="#2f2f2f", font=("Consolas", 36, "bold"),
                              command=lambda: [self.close_all_overlays(), self.find_match()])
        start_button.pack(pady=300)

        # ABOUT SECTION
        with open("about.txt", "r", encoding="utf-8") as file:
            about_content_data = file.read()
        text_label = Label(about_content, text=about_content_data, font=("Consolas", 12), fg="white", bg="black",
                           justify="left", wraplength=1400)
        text_label.pack(anchor="nw", padx=50, pady=50)

        # LEARN SECTION

        learn_container = Frame(learn_content, bg="black")
        learn_container.pack(fill="both", expand=True, padx=50)

        # TITLE / BUTTONS AREA

        title = Label(
            learn_container,
            text="CTF TRAINING",
            font=("Consolas", 26, "bold"),
            fg="white",
            bg="black"
        )
        title.pack(pady=30)

        # LOAD IMAGE

        try:
            pil_img = Image.open("pictures/Example_code1.PNG")

            width_size = 800
            w_percent = width_size / float(pil_img.size[0])
            h_size = int(float(pil_img.size[1]) * w_percent)

            pil_img = pil_img.resize((width_size, h_size), Image.Resampling.LANCZOS)

            learn_image_tk = ImageTk.PhotoImage(pil_img)

        except Exception as e:
            print("Image load error:", e)
            learn_image_tk = None

        # READ FILE

        with open("learn.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()

        # RENDER CONTENT (TEXT + IMAGE)

        for i, line in enumerate(lines):

            label = Label(
                learn_container,
                text=line.strip(),
                font=("Consolas", 14),
                fg="white",
                bg="black",
                anchor="w",
                wraplength=1200
            )
            label.pack(pady=2, anchor="w")

            # вставка картинки после строки 32
            if i == 32 and learn_image_tk:
                img_label = Label(
                    learn_container,
                    image=learn_image_tk,
                    bg="black"
                )
                img_label.image = learn_image_tk
                img_label.pack(pady=40)

        # TOOLS BLOCK

        tools_box = Frame(learn_container, bg="#2f2f2f")

        Button(
            tools_box,
            text="ASCII Table",
            font=("Consolas", 15, "bold"),
            fg="white",
            bg="black",
            command=lambda: webbrowser.open("https://ascii.co.uk/info")
        ).pack(pady=5)

        Button(
            tools_box,
            text="CyberChef",
            font=("Consolas", 15, "bold"),
            fg="white",
            bg="black",
            command=lambda: webbrowser.open("https://gchq.github.io/CyberChef/")
        ).pack(pady=5)

        Button(
            tools_box,
            text="XOR Calculator",
            font=("Consolas", 15, "bold"),
            fg="white",
            bg="black",
            command=lambda: webbrowser.open("https://xor.pw/#")
        ).pack(pady=5)

        Button(
            tools_box,
            text="Python Tutor",
            font=("Consolas", 15, "bold"),
            fg="white",
            bg="black",
            command=lambda: webbrowser.open("https://pythontutor.com/visualize.html")
        ).pack(pady=5)

        Button(
            tools_box,
            text="Python Docs",
            font=("Consolas", 15, "bold"),
            fg="white",
            bg="black",
            command=lambda: webbrowser.open("https://docs.python.org/3/")
        ).pack(pady=5)

        tools_box.pack(pady=50, padx=100, fill="x")

        # SCOREBOARD SECTION

        self.score = Label(self.scoreboard_content, fg="white", bg="black", font=("Consolas", 24, "bold"),
                           cursor="hand2")
        self.score.grid(row=0, column=0, columnspan=3, pady=10)

        self.challenges_content.columnconfigure(0, weight=1)
        self.challenges_content.columnconfigure(1, weight=0)
        self.challenges_content.columnconfigure(2, weight=0)
        self.challenges_content.columnconfigure(3, weight=1)

        self.result_frame = Frame(self.root, bg="#2f2f2f", width=500, height=100)
        self.result_label = Label(self.result_frame, text="", fg="white", bg="#2f2f2f", font=("Consolas", 16, "bold"))
        self.result_label.place(relx=0.5, rely=0.5, anchor=CENTER)

        # WAITING ROOM SECTION

        title_wait = Label(self.waiting_room_frame, text="Waiting for the second player", fg="white", bg="#2f2f2f",
                           font=("Consolas", 36, "bold"))
        title_wait.place(relx=0.5, y=100, anchor=CENTER)

        self.you_played_all_games_label = Label(self.root, text="You have finished all rounds, congrats!", fg="white",
                                                bg="#2f2f2f", font=("Consolas", 16, "bold"))

        # GAME FRAME SECTION


        title_game = Label(self.game_frame, text="You are in the game!", fg="white", bg="#2f2f2f",
                           font=("Consolas", 10, "bold"))
        title_game.place(relx=0.5, y=40, anchor=CENTER)

        time_lbl = Label(self.game_frame, text="Time:", fg="white", bg="#2f2f2f", font=("Consolas", 15, "bold"))
        time_lbl.place(relx=0.8, y=100, anchor="w")

        self.timer = Label(self.game_frame, font=("Consolas", 15, "bold"), fg="white", bg="#2f2f2f")
        self.timer.place(relx=0.85, y=100, anchor="w")

        self.game_opponent = Label(self.game_frame, text=f"Your opponent: {self.current_opponent}", fg="white",
                                   bg="#2f2f2f", font=("Consolas", 15, "bold"))
        self.game_opponent.place(relx=0.8, y=150, anchor="w")

        self.game_score_label = Label(self.game_frame, text=f"Your score: {self.your_game_score}", fg="white",
                                      bg="#2f2f2f", font=("Consolas", 15, "bold"))
        self.game_score_label.place(relx=0.8, y=200, anchor="w")

        self.opponent_score_label = Label(self.game_frame, text=f"Opponent's score: {self.opponent_game_score}",
                                          fg="white", bg="#2f2f2f", font=("Consolas", 15, "bold"))
        self.opponent_score_label.place(relx=0.8, y=250, anchor="w")

        self.ascii_label = None
        self.ascii_tk_image = None

        self.tools_button = Button(self.game_frame, text="Tools", font=("Consolas", 15, "bold"), fg="white", bg="black",
                             command=self.toggle_tools_window)
        self.tools_button.place(relx=0.8, rely=0.45, anchor="w")

        # Tools screen

        self.tools_frame = Frame(self.root, bg="#2f2f2f", width=200, height=300)

        self.ascii_button = Button(self.tools_frame, text="ASCII Table", font=("Consolas", 15, "bold"), fg="white", bg="black",
                                   command=lambda: webbrowser.open("https://ascii.co.uk/info"))
        self.ascii_button.place(relx=0.5, rely=0.167, anchor=CENTER)

        # CyberChef button
        self.cyber_button = Button(self.tools_frame, text="CyberChef", font=("Consolas", 15, "bold"), fg="white",
                                   bg="black",
                                   command=lambda: webbrowser.open("https://gchq.github.io/CyberChef/"))
        self.cyber_button.place(relx=0.5, rely=0.334, anchor=CENTER)

        # XOR Calculator button
        self.pydocs_button = Button(self.tools_frame, text="XOR Calculator", font=("Consolas", 15, "bold"), fg="white",
                                    bg="black",
                                    command=lambda: webbrowser.open(
                                        "https://xor.pw/#"))
        self.pydocs_button.place(relx=0.5, rely=0.501, anchor=CENTER)

        # Python Tutor button
        self.pytutor_button = Button(self.tools_frame, text="Python Tutor", font=("Consolas", 15, "bold"), fg="white",
                                     bg="black",
                                     command=lambda: webbrowser.open("https://pythontutor.com/visualize.html"))
        self.pytutor_button.place(relx=0.5, rely=0.668, anchor=CENTER)

        # Official Python Documentation button
        self.pydocs_button = Button(self.tools_frame, text="Python Docs", font=("Consolas", 15, "bold"), fg="white",
                                    bg="black",
                                    command=lambda: webbrowser.open(
                                        "https://docs.python.org/ru/3/library/stdtypes.html"))
        self.pydocs_button.place(relx=0.5, rely=0.8335, anchor=CENTER)



        # END OF THE GAME SECTION


        Label(self.end_of_game_frame, text="GAME OVER!", fg="white", bg="black", font=("Consolas", 36, "bold")).place(
            relx=0.5, rely=0.3, anchor=CENTER)

        self.who_won_label = Label(self.end_of_game_frame, text="", font=("Consolas", 20, "bold"), bg="#2f2f2f",
                                   fg="white")
        self.who_won_label.place(relx=0.5, rely=0.5, anchor=CENTER)

        self.score_label = Label(self.end_of_game_frame, text="", font=("Consolas", 20, "bold"), bg="#2f2f2f",
                                 fg="white")
        self.score_label.place(relx=0.5, rely=0.6, anchor=CENTER)

        back_button = Button(self.end_of_game_frame, text="Back", font=("Consolas", 24, "bold"), fg="white", bg="red",
                             command=lambda: [self.close_all_overlays(), self.show_frame(self.main_menu_frame),
                                              self.show_frame(self.menu_frame)])
        back_button.place(relx=0.9, rely=0.1, anchor=CENTER)







        self.show_frame(Start)


# =========================================================
# UI CLASSES FOR TASKS
# =========================================================

class TaskCard:
    def __init__(self, app, parent, info, row, column, is_opened, mode="library"):
        self.app = app
        self.info = info
        self.is_opened = is_opened
        self.mode = mode

        self.reduced_points = None

        if self.is_opened:
            self.bg_color = "#2f2f2f"
            self.text_color = "white"
        else:
            self.bg_color = "#1a1a1a"
            self.text_color = "#777777"

        if self.mode == "game":
            pady = 15
            padx = 40
            sticky = "w"
        else:
            pady = 40
            padx = 40
            sticky = None

        self.frame = Frame(parent, bg=self.bg_color, width=450, height=120)
        self.frame.grid(row=row, column=column, padx=padx, pady=pady, sticky=sticky)
        self.frame.grid_propagate(False)

        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)

        self.title = Label(self.frame, text=info["title"], fg=self.text_color, bg=self.bg_color,
                           font=("Consolas", 16, "bold"))
        self.title.grid(row=0, column=0, sticky="w", padx=20, pady=(10, 0))

        self.difficulty = Label(self.frame, text=info["difficulty"], fg=self.text_color, bg=self.bg_color,
                                font=("Consolas", 12, "bold"))
        self.difficulty.grid(row=0, column=1, sticky="e", padx=20, pady=(10, 0))

        if self.mode == "library" and self.is_opened:
            self.points = Label(self.frame, text=f"{info['points']} points", fg="white", bg=self.bg_color,
                                font=("Consolas", 12, "bold overstrike"))
            self.points.grid(row=1, column=0, sticky="w", padx=(20, 5), pady=(5, 5))

            self.reduced_points = Label(self.frame, text=f"{info['reduced_points']} points", fg="white",
                                        bg=self.bg_color, font=("Consolas", 12, "bold"))
            self.reduced_points.grid(row=1, column=0, sticky="w", padx=(120, 100), pady=(5, 5))
        else:
            self.points = Label(self.frame, text=f"{info['points']} points", fg=self.text_color, bg=self.bg_color,
                                font=("Consolas", 12, "bold"))
            self.points.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(5, 5))

        self.type_label = Label(self.frame, text=info["type"], fg=self.text_color, bg=self.bg_color,
                                font=("Consolas", 12, "bold"))
        self.type_label.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 10))

        self.solves = Label(self.frame, text=f"{info['solves']} solves", fg=self.text_color, bg=self.bg_color,
                            font=("Consolas", 12, "bold"))
        self.solves.grid(row=2, column=1, sticky="e", padx=20, pady=(0, 10))

        self.task_frame_page = Frame(self.app.challenges_content, bg=self.bg_color, width=1280, height=720)

        self.status_label = Label(self.frame, text="", fg="green", bg=self.bg_color,
                                  font=("Consolas", 12, "bold"))
        self.status_label.place(relx=0.6, rely=0.2, anchor="center")

        if info["id"] in self.app.current_user["solved_tasks"]:
            self.status_label.config(text="Completed", fg="green")

        if self.is_opened:
            widgets = [
                self.frame, self.title, self.difficulty, self.points,
                self.type_label, self.solves, self.status_label
            ]
            if self.reduced_points is not None:
                widgets.append(self.reduced_points)

            for widget in widgets:
                widget.bind("<Enter>", self.on_enter)
                widget.bind("<Leave>", self.on_leave)
                widget.bind("<Button-1>", self.open_task)

    def on_enter(self, event):
        self.frame.config(bg="#4d4d4d")
        lbl_list = [self.title, self.difficulty, self.points, self.type_label, self.solves, self.status_label]
        if self.reduced_points is not None:
            lbl_list.append(self.reduced_points)

        for lbl in lbl_list:
            lbl.config(bg="#4d4d4d", fg="#bfbfbf")

    def on_leave(self, event):
        self.frame.config(bg="#2f2f2f")
        self.title.config(bg="#2f2f2f", fg="white")
        self.difficulty.config(bg="#2f2f2f", fg="white")
        self.points.config(bg="#2f2f2f", fg="white")
        self.type_label.config(bg="#2f2f2f", fg="white")
        self.solves.config(bg="#2f2f2f", fg="white")
        self.status_label.config(bg="#2f2f2f", fg="green")
        if self.reduced_points is not None:
            self.reduced_points.config(bg="#2f2f2f", fg="white")

    def open_task(self, event):
        task_id = self.info["id"]
        print(f"Requesting task {task_id}")

        enc_id = self.app.cipher.encrypt(str(task_id)).hex()
        self.app.protocol.send_msg("get_task_page", enc_id)
        print("Request sent")


class TaskPage:
    def __init__(self, app, info, mode):
        self.app = app
        self.info = info
        self.mode = mode

        self.frame = Frame(self.app.root, bg="#0f172a", width=1280, height=720)
        self.frame.place(relx=0.5, rely=0.5, anchor=CENTER)

        self.title = Label(self.frame, text=self.info["title"], font=("Consolas", 24, "bold"), fg="white", bg="#0f172a")
        self.title.place(x=50, y=20)

        if self.mode == "library":
            self.points = Label(self.frame, text=f"{info['points']}", fg="white", bg="#0f172a",
                                font=("Consolas", 24, "bold", "overstrike"))
            self.points.place(x=275, y=20)

            self.reduced_points = Label(self.frame, text=f"{info['reduced_points']}", fg="white",
                                        bg="#0f172a", font=("Consolas", 24, "bold"))
            self.reduced_points.place(x=340, y=20)
        else:
            self.points = Label(self.frame, text=self.info["points"], font=("Consolas", 24, "bold"), fg="white",
                                bg="#0f172a")
            self.points.place(x=300, y=20)

        self.difficult = Label(self.frame, text=self.info["difficulty"], font=("Consolas", 24, "bold"), fg="white",
                               bg="#0f172a")
        self.difficult.place(x=500, y=20)

        self.description = Label(self.frame, text=self.info["description"], font=("Consolas", 24, "bold"), fg="white",
                                 bg="#0f172a")
        self.description.place(x=50, y=150)

        self.files = Label(self.frame, text="Attachments:", font=("Consolas", 24, "bold"), fg="white", bg="#0f172a")
        self.files.place(x=50, y=300)

        self.download = Label(self.frame, text=self.info["files"], fg="#66ccff", bg="#0f172a", font=("Consolas", 14),
                              cursor="hand2")
        self.download.place(x=300, y=310)

        self.download.bind("<Button-1>", lambda e: [self.download_folder(), self.download.config(fg="white", font=(
        "Consolas", 14, "underline"))])
        self.download.bind("<ButtonRelease-1>",
                           lambda e: self.download.config(fg="#66ccff", font=("Consolas", 14, "underline")))
        self.download.bind("<Enter>", lambda e: self.download.config(font=("Consolas", 14, "underline"), fg="#66ccff"))
        self.download.bind("<Leave>", lambda e: self.download.config(font=("Consolas", 14), fg="#66ccff"))

        self.back_button = Button(self.frame, text="Back", font=("Consolas", 24, "bold"), fg="white", bg="red",
                                  command=self.close)
        self.back_button.place(x=1120, y=20)

        self.enter_flag_label = Label(self.frame, text="Enter the flag:", fg="white", bg="#0f172a",
                                      font=("Consolas", 24, "bold"))
        self.enter_flag_label.place(x=50, y=600)

        self.enter_flag = Entry(self.frame, width=30, font=("Consolas", 14, "bold"))
        self.enter_flag.place(x=350, y=610)

        self.submit = Button(self.frame, text="Submit", fg="white", bg="#020617", font=("Consolas", 14, "bold"),
                             command=self.submit_flag)
        self.submit.place(x=700, y=600)

        self.completed_label = Label(self.frame, text=f"You already solved this task", fg="green", bg="#0f172a",
                                     font=("Consolas", 14, "bold"))

        if info["id"] in self.app.current_user["solved_tasks"]:
            self.enter_flag.pack_forget()
            self.submit.pack_forget()
            self.completed_label.place(relx=0.8, y=620, anchor="center")

    def download_folder(self):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        source_file = self.info["files"][0]
        destination = os.path.join(downloads, source_file)
        shutil.copy(source_file, destination)
        print(f"File {source_file} copied to {destination}")

    def update_status(self):
        if self.info["id"] in self.app.current_user["solved_tasks"]:
            self.status_label.config(text="Completed", fg="green")

    def submit_flag(self):
        user_flag = self.enter_flag.get()
        print(f"User flag: {user_flag}")

        if self.mode == "game":
            if not self.app.game_active:
                print("Game is over — ignoring submit")
                return
            msg_type = "submit_game_flag"
        elif self.mode == "library":
            msg_type = "submit_library_flag"

        self.app.last_submitted_flag = user_flag

        enc_id = self.app.cipher.encrypt(str(self.info["id"])).hex()
        enc_flag = self.app.cipher.encrypt(user_flag).hex()
        self.app.protocol.send_msg(msg_type, enc_id, enc_flag)

    def close(self):
        self.frame.destroy()


# =========================================================
# APPLICATION ENTRY POINT
# =========================================================

def main():
    root_window = Tk()
    root_window.title("CTF")
    root_window.geometry("1280x720")

    app = Client(root=root_window, host="127.0.0.1", port=5555)

    app.build_ui()

    app.show_frame(app.log_in_frame)
    root_window.mainloop()


if __name__ == "__main__":
    main()