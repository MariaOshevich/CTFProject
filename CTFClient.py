from tkinter import*
import socket
import threading
import shutil
import os
import json

from Protocol import Protocol

# Functions

def show_frame(frame):
    frame.tkraise()

def send_signup():
    nickname1 = nickname_signup_entry.get()
    password1 = password_signup_entry.get()

    protocol.send_msg("signup", nickname1, password1)

def send_login():
    nickname = nickname_login_entry.get()
    password = password_login_entry.get()

    protocol.send_msg("login", nickname, password)

def find_match():
    nickname2 = nickname_login_entry.get()
    password2 = password_login_entry.get()

    protocol.send_msg("find_match", nickname2, password2)
    show_frame(waiting_room_frame)







def listen_server():
    while True:
        msg_type, args = protocol.get_msg()
        if not msg_type:
            break

        print("DEBUG:", msg_type, args)

        if msg_type == "success":
            handle_success(args)

        elif msg_type == "error":
            handle_error(args)

        elif msg_type == "tasks_card":
            handle_task_card(args)


        elif msg_type == "tasks_page_opened":
            handle_task_page_opened(args)

        elif msg_type == "tasks_page_locked":
            handle_task_data_locked(args)

        elif msg_type == "your_score":
            handle_score(args)


        elif msg_type == "wait":
            print("Waiting for the second player")

        elif msg_type == "start":
            print("Game started!")
            show_frame(game_frame)
            update_timer()

def enter_main_menu(nickname=None):

    show_frame(main_menu_frame)
    show_frame(menu_frame)


    if nickname is None:
        nickname = nickname_login_entry.get()

    title = Label(menu_frame, text=f"Welcome, {nickname}",
                  fg="white", bg="#0f172a",
                  font=("Consolas", 24, "bold"))
    title.place(relx=0.15, rely=0.5, anchor=CENTER)


    protocol.send_msg("get_task_card")
    protocol.send_msg("score")

def handle_success(args):
    enter_main_menu()

def handle_registration_success(args):
    nickname = nickname_signup_entry.get()
    enter_main_menu(nickname)

def handle_error(args):
    error_label1.place(relx=0.4, y=500)

def handle_task_card(args):
    data = json.loads(args[0])

    tasks = data["tasks"]
    opened_tasks = data["opened_tasks"]

    for widget in challenges_content.winfo_children():
        widget.destroy()

    for i, task in enumerate(tasks):
        r = i // 2
        c = i % 2

        is_opened = task["id"] in opened_tasks

        TaskCard(challenges_content, task, r, c + 1, is_opened)

def handle_task_page_opened(args):
    task_data = json.loads(args[0])

    print("Task is opened:", task_data["title"])

    TaskPage(task_data)


def handle_task_data_locked(args):
    task_id = args[0]

    print(f"Task {task_id} is closed")

def handle_score(args):
    score = Label(scoreboard_content, text=f"Your score: {args[0]}", fg="white", bg="black", font=("Consolas", 24, "bold"),
                  cursor="hand2")
    score.pack(pady=300)





seconds = 10 * 60
def update_timer():
    global seconds
    minutes = seconds // 60
    sec = seconds % 60
    timer.config(text=f"{minutes}:{sec:02}")
    seconds -= 1
    game_frame.after(1000, update_timer)





# Client part

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("127.0.0.1", 9001))

protocol = Protocol(client_socket)


threading.Thread(target=listen_server, daemon=True).start()


root = Tk()

root.title('CTF')
root.geometry('1280x720')

container = Frame(root)
container.place(x=0, y=0, relwidth=1, relheight=1)


# Frame container

log_in_frame = Frame(container, bg="#719bf0")
sign_up_frame = Frame(container, bg="#719bf0")
main_menu_frame = Frame(container, bg="#d16676")
waiting_room_frame = Frame(container, bg="#f5bf73")
game_frame = Frame(container, bg="#6ccc96")

for f in (log_in_frame, sign_up_frame, main_menu_frame, waiting_room_frame, game_frame):
    f.place(x=0, y=0, relwidth=1, relheight=1)



# log_in_frame

title = Label(log_in_frame, text="Capture The Flag", fg="white", bg="#0f172a", font=("Consolas", 36, "bold"))
title.place(relx=0.5, y=100, anchor=CENTER)

Label(log_in_frame, text="Log in", fg="white", bg="#0f172a", font=("Consolas", 24)).place(relx=0.5, y=200, anchor=CENTER)

Label(log_in_frame, text="Nickname", fg="white", bg="#020617", font=("Consolas", 14)
).place(relx=0.4, y=260)

nickname_login_entry = Entry(log_in_frame, font=("Consolas", 14), width=30)
nickname_login_entry.place(relx=0.4, y=290)


Label(log_in_frame, text="Password", fg="white", bg="#020617", font=("Consolas", 14)
).place(relx=0.4, y=340)

password_login_entry = Entry(log_in_frame, font=("Consolas", 14), width=30, show="*")
password_login_entry.place(relx=0.4, y=370)

log_in_button = Button(log_in_frame, text="Log in", fg="white", bg="#020617", font=("Consolas", 14), command = send_login,
)
log_in_button.place(relx=0.4, y=430)

sign_up_link = Label(log_in_frame, text="Don't have an account? Click here", fg="red", font=("Consolas", 14), cursor="hand2")
sign_up_link.place(relx=0.4, y=580)
sign_up_link.bind("<Button-1>", lambda e: show_frame(sign_up_frame))

error_label1 = Label(log_in_frame, text="Nickname or password are wrong", fg="red", bg=log_in_frame["bg"], font=("Consolas", 12))



# sign_up_frame

title1 = Label(sign_up_frame, text="CTF", fg="white", bg="#0f172a", font=("Consolas", 36, "bold"))
title1.place(relx=0.5, y=100, anchor=CENTER)

Label(sign_up_frame, text="Sign up", fg="white", bg="#0f172a", font=("Consolas", 24)).place(relx=0.5, y=200, anchor=CENTER)

Label(sign_up_frame, text="Nickname", fg="white", bg="#020617", font=("Consolas", 14)
).place(relx=0.4, y=260)

nickname_signup_entry = Entry(sign_up_frame, font=("Consolas", 14), width=30)
nickname_signup_entry.place(relx=0.4, y=290)


Label(sign_up_frame, text="Password", fg="white", bg="#020617", font=("Consolas", 14)
).place(relx=0.4, y=340)

password_signup_entry = Entry(sign_up_frame, font=("Consolas", 14), width=30, show="*")
password_signup_entry.place(relx=0.4, y=370)

sign_up_button = Button(sign_up_frame, text="Sign up", fg="white", bg="#020617", font=("Consolas", 14), command=send_signup
)
sign_up_button.place(relx=0.4, y=430)

sign_up_link = Label(sign_up_frame, text="Go back to the Log in page", fg="red", font=("Consolas", 14), cursor="hand2")
sign_up_link.place(relx=0.4, y=580)
sign_up_link.bind("<Button-1>", lambda e: show_frame(log_in_frame))

error_label2 = Label(sign_up_frame, text="This nickname is already taken", fg="red", bg=log_in_frame["bg"], font=("Consolas", 12))




#main_menu_frame


def create_scrollable_frame(parent, bg_color):
    canvas = Canvas(parent, bg=bg_color, highlightthickness=0)
    scrollbar = Scrollbar(parent, orient="vertical", command=canvas.yview)

    scrollable_frame = Frame(canvas, bg=bg_color)

    window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def update_scrollregion(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    scrollable_frame.bind("<Configure>", update_scrollregion)

    def resize_frame(event):
        canvas.itemconfig(window_id, width=event.width)

    canvas.bind("<Configure>", resize_frame)

    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return scrollable_frame

# main menu pages

main_menu_frame = Frame(container, bg="#d16676")
main_menu_frame.place(x=0, y=100, relwidth=1, relheight=1, anchor="nw")  # прямо под меню

# Fixed menu at the top

menu_frame = Frame(container, bg="#0f172a", height=100, width=1600)
menu_frame.place(x=0, y=0, relwidth=1)


Profile = Frame(main_menu_frame, bg="black")

About = Frame(main_menu_frame, bg="red")
Learn = Frame(main_menu_frame, bg="blue")
Challenges = Frame(main_menu_frame, bg="green")
Scoreboard = Frame(main_menu_frame, bg="yellow")

Start = Frame(main_menu_frame, bg="purple")

for frame in (About, Learn, Challenges, Scoreboard, Profile, Start):
    frame.place(x=0, y=0, relwidth=1, relheight=1)

# Scrollable areas

profile_content = create_scrollable_frame(Profile, "black")
about_content = create_scrollable_frame(About, "#0d0d0d")
learn_content = create_scrollable_frame(Learn, "blue")
challenges_content = create_scrollable_frame(Challenges, "green")
scoreboard_content = create_scrollable_frame(Scoreboard, "yellow")
start_content = create_scrollable_frame(Start, "purple")




# Button menu

Button(menu_frame, text="About", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a", command=lambda: show_frame(About)).place(relx=0.5, y=50, anchor=CENTER)
Button(menu_frame, text="Learn", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a", command=lambda: show_frame(Learn)).place(relx=0.6, y=50, anchor=CENTER)
Button(menu_frame, text="Challenges", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a", command=lambda: show_frame(Challenges)).place(relx=0.7, y=50, anchor=CENTER)
Button(menu_frame, text="Scoreboard", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a", command=lambda: show_frame(Scoreboard)).place(relx=0.8, y=50, anchor=CENTER)

Button(menu_frame, text="Profile", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a", command=lambda: show_frame(Profile)).place(x=1400, y=50, anchor=CENTER)

Button(menu_frame, text="Start", width=12, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a",
           command=lambda: show_frame(Start)).place(relx=0.4, y=50, anchor=CENTER)




show_frame(Start)

# Start section

start_button = Button(start_content, text="Start", fg="white", bg="#0f172a", font=("Consolas", 36, "bold"), command=find_match)
start_button.pack(pady=300)


# About section


with open("text.txt", "r", encoding="utf-8") as file:
    content = file.read()

text_label = Label(
    about_content,
    text=content,
    font=("Consolas", 12),
    fg="white",
    bg="#0d0d0d",
    justify="left",
    wraplength=1400
)
text_label.pack(anchor="nw", padx=50, pady=50)



class TaskCard:
    def __init__(self, parent, info, row, column, is_opened):
        self.info = info
        self.is_opened = is_opened

        if self.is_opened:
            self.bg_color = "#333333"
            self.text_color = "white"

        else:
            self.bg_color = "#1a1a1a"
            self.text_color = "#777777"



        self.frame = Frame(parent, bg=self.bg_color, width=450, height=120)

        self.frame.grid(row=row, column=column, padx=40, pady=40)
        self.frame.grid_propagate(False)

        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)

        self.title = Label(self.frame, text=info["title"], fg=self.text_color, bg=self.bg_color,
                           font=("Consolas", 16, "bold"))
        self.title.grid(row=0, column=0, sticky="w", padx=20, pady=(10, 0))

        self.difficulty = Label(self.frame, text=info["difficulty"], fg=self.text_color, bg=self.bg_color,
                                font=("Consolas", 12, "bold"))
        self.difficulty.grid(row=0, column=1, sticky="e", padx=20, pady=(10, 0))

        self.points = Label(self.frame, text=info["points"], fg=self.text_color, bg=self.bg_color,
                            font=("Consolas", 12, "bold"))
        self.points.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(5, 5))

        self.type_label = Label(self.frame, text=info["type"], fg=self.text_color, bg=self.bg_color,
                                font=("Consolas", 12, "bold"))
        self.type_label.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 10))

        self.solves = Label(self.frame, text=info["solves"], fg=self.text_color, bg=self.bg_color,
                            font=("Consolas", 12, "bold"))
        self.solves.grid(row=2, column=1, sticky="e", padx=20, pady=(0, 10))

        self.task_frame_page = Frame(challenges_content, bg=self.bg_color, width=1280, height=720)


        if self.is_opened:
            for widget in [self.frame, self.title, self.difficulty, self.points, self.type_label, self.solves]:
                widget.bind("<Enter>", self.on_enter)
                widget.bind("<Leave>", self.on_leave)
                widget.bind("<Button-1>", self.open_task)


    def on_enter(self, event):
        self.frame.config(bg="#0b1220")
        for lbl in [self.title, self.difficulty, self.points, self.type_label, self.solves]:
            lbl.config(bg="#0b1220", fg="#bfbfbf")

    def on_leave(self, event):
        self.frame.config(bg="#333333")
        self.title.config(bg="#333333", fg="white")
        self.difficulty.config(bg="#333333", fg="white")
        self.points.config(bg="#333333", fg="white")
        self.type_label.config(bg="#333333", fg="white")
        self.solves.config(bg="#333333", fg="white")

    def open_task(self, event):
        task_id = self.info["id"]

        print(f"Requesting task {task_id}")

        protocol.send_msg("get_task_page", str(task_id))

        print("Request sent")



challenges_content.columnconfigure(0, weight=1)
challenges_content.columnconfigure(1, weight=0)
challenges_content.columnconfigure(2, weight=0)
challenges_content.columnconfigure(3, weight=1)



class TaskPage():
    def __init__(self, info):
        self.frame = Frame(root, bg="#0f172a", width=1280, height=720)
        self.frame.place(relx=0.5, rely=0.5, anchor=CENTER)

        self.info = info

        self.title = Label(self.frame, text=self.info["title"], font=("Consolas", 24, "bold"), fg="white", bg="#0f172a")
        self.title.place(x=50, y=20)

        self.points = Label(self.frame, text=self.info["points"], font=("Consolas", 24, "bold"), fg="white", bg="#0f172a")
        self.points.place(x=300, y=20)

        self.difficult = Label(self.frame, text=self.info["difficulty"], font=("Consolas", 24, "bold"), fg="white",bg="#0f172a")
        self.difficult.place(x=500, y=20)

        self.description = Label(self.frame, text=self.info["description"], font=("Consolas", 24, "bold"), fg="white",bg="#0f172a")
        self.description.place(x=50, y=150)



        self.files = Label(self.frame, text="Attachments:", font=("Consolas", 24, "bold"),
                                 fg="white", bg="#0f172a")
        self.files.place(x=50, y=300)

        def download_folder():
            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            source_file = self.info["files"][0]
            destination = os.path.join(downloads, source_file)
            shutil.copy(source_file, destination)
            print(f"File {source_file} copied to {destination}")

        self.download = Label(self.frame, text=self.info["files"], fg="#66ccff", bg="#0f172a", font=("Consolas", 14), cursor="hand2")

        self.download.place(x=300, y=310)
        self.download.bind("<Button-1>", lambda e: [download_folder(), self.download.config(fg="white", font=("Consolas", 14, "underline"))])
        self.download.bind("<ButtonRelease-1>", lambda e: self.download.config(fg="#66ccff", font=("Consolas", 14, "underline")))
        self.download.bind("<Enter>", lambda e: self.download.config(font=("Consolas", 14, "underline"), fg="#66ccff"))
        self.download.bind("<Leave>", lambda e: self.download.config(font=("Consolas", 14), fg="#66ccff"))


        self.back_button = Button(self.frame, text="Back", font=("Consolas", 24, "bold"), fg="white", bg="red", command=self.close)
        self.back_button.place(x=1120, y=20)

        self.enter_flag_label = Label(self.frame, text="Enter the flag:", fg="white", bg="#0f172a", font=("Consolas", 24, "bold"))
        self.enter_flag_label.place(x=50, y=600)

        self.enter_flag = Entry(self.frame, width=30, font=("Consolas", 14, "bold"))
        self.enter_flag.place(x=350, y=610)

        self.submit = Button(self.frame, text="Submit", fg="white", bg="#020617", font=("Consolas", 14, "bold"), command=self.submit_flag)
        self.submit.place(x=700, y=600)

    def submit_flag(self):
        user_flag = self.enter_flag.get()
        print(f"User flag: {user_flag}")

    def close(self):
        self.frame.destroy()

# Score section

score = Label(scoreboard_content, text=f"Your score: {67}", fg="white", bg="black", font=("Consolas", 14), cursor="hand2")
sign_up_link.place(relx=0.4, y=580)












#waiting_room_frame

title = Label(waiting_room_frame, text="Waiting for the second player", fg="white", bg="#0f172a", font=("Consolas", 36, "bold")
)
title.place(relx=0.5, y=100, anchor=CENTER)

#game_frame

title = Label(game_frame, text="You are in the game!", fg="white", bg="#0f172a", font=("Consolas", 10, "bold")
)
title.place(relx=0.5, y=40, anchor=CENTER)

time = Label(game_frame, text="Time:", fg="white", bg="#0f172a", font=("Consolas", 15, "bold")
)
time.place(relx=0.8, y=100, anchor=CENTER)

timer = Label(game_frame, font=("Consolas", 15, "bold"), fg="white", bg="#0f172a")
timer.place(relx=0.85, y=100, anchor=CENTER)


show_frame(log_in_frame)
root.mainloop()
