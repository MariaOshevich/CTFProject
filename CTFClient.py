from tkinter import*
import socket
import threading

from Protocol import Protocol

# Functions

def show_frame(frame):  # Откроет указанный фрейм
    frame.tkraise()

def send_signup():
    nickname1 = nickname_signup_entry.get()
    password1 = password_signup_entry.get()

    protocol.send_msg("signup", nickname1, password1)

    msg_type, args = protocol.get_msg()

    if msg_type == "success":
        show_frame(main_menu_frame)
    elif msg_type == "error":
        error_label2.place(relx=0.4, y=500)

def send_login():
    nickname2 = nickname_login_entry.get()
    password2 = password_login_entry.get()

    protocol.send_msg("login", nickname2, password2)

    msg_type, args = protocol.get_msg()

    if msg_type == "success":
        show_frame(main_menu_frame)
        title = Label(main_menu_frame, text=f"Welcome, {nickname2}", fg="white", bg="#0f172a", font=("Consolas", 36, "bold"))
        title.place(relx=0.5, y=100, anchor=CENTER)
    elif msg_type == "error":
        error_label1.place(relx=0.4, y=500)

def find_match():
    nickname2 = nickname_login_entry.get()
    password2 = password_login_entry.get()

    protocol.send_msg("find_match", nickname2, password2)
    show_frame(waiting_room_frame)
    threading.Thread(target=listen_server, daemon=True).start()

def listen_server():
    while True:
        msg_type, args = protocol.get_msg()
        if not msg_type:
            break

        elif msg_type == "wait":
            print("Waiting for the second player")
        elif msg_type == "start":
            print("Game started!")
            show_frame(game_frame)
            break





# Client part

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Создаем клиент
client_socket.connect(("127.0.0.1", 9000)) # Подключаем клиент к указанному порту и хосту (серверу)

protocol = Protocol(client_socket)




root = Tk()

root.title('CTF Attack the city')
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

title = Label(log_in_frame, text="CTF: Attack the City", fg="white", bg="#0f172a", font=("Consolas", 36, "bold"))
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

title1 = Label(sign_up_frame, text="CTF: Attack the City", fg="white", bg="#0f172a", font=("Consolas", 36, "bold"))
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

start_button = Button(main_menu_frame, text="Start", fg="white", bg="#0f172a", font=("Consolas", 36, "bold"), command=find_match)
start_button.place(relx=0.5, y=300, anchor=CENTER)
'''start_button.bind("<Button-1>", lambda e: show_frame(waiting_room_frame))'''

#waiting_room_frame

title = Label(waiting_room_frame, text="Waiting for the second player", fg="white", bg="#0f172a", font=("Consolas", 36, "bold")
)
title.place(relx=0.5, y=100, anchor=CENTER)

#game_frame

title = Label(game_frame, text="You are in the game!", fg="white", bg="#0f172a", font=("Consolas", 36, "bold")
)
title.place(relx=0.5, y=100, anchor=CENTER)



show_frame(log_in_frame)
root.mainloop()
