
import customtkinter as ctk
import socket
import threading
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Syntrix(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Syntrix | Network Security Monitor")
        self.geometry("950x650")

        self.running = False
        self.server = None
        self.clients = set()
        self.lock = threading.Lock()

        ctk.CTkLabel(
            self,
            text="SYNTRIX",
            font=("Arial", 30, "bold")
        ).pack(pady=20)

        ctk.CTkLabel(
            self,
            text="Network Security Monitoring Dashboard"
        ).pack()

        frame = ctk.CTkFrame(self)
        frame.pack(pady=20, padx=20, fill="x")

        self.ip = ctk.CTkEntry(
            frame, width=200
        )
        self.ip.insert(0, "0.0.0.0")
        self.ip.pack(side="left", padx=15, pady=15)

        self.port = ctk.CTkEntry(
            frame, width=120
        )
        self.port.insert(0, "5555")
        self.port.pack(side="left", padx=10)

        self.start_btn = ctk.CTkButton(
            frame,
            text="Start Monitoring",
            command=self.start_monitor
        )
        self.start_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(
            frame,
            text="Stop",
            command=self.stop_monitor,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)

        self.status = ctk.CTkLabel(
            self,
            text="Status: Offline",
            text_color="gray"
        )
        self.status.pack(pady=10)

        self.logs = ctk.CTkTextbox(
            self,
            font=("Courier New", 13)
        )
        self.logs.pack(
            padx=20, pady=15,
            fill="both", expand=True
        )

        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")

        def update():
            if self.winfo_exists():
                self.logs.insert(
                    "end", f"[{timestamp}] {message}\n"
                )
                self.logs.see("end")

        self.after(0, update)

    def set_status(self, message, color):
        self.after(
            0,
            lambda: self.status.configure(
                text=message,
                text_color=color
            )
        )

    def start_monitor(self):
        if self.running:
            return

        host = self.ip.get().strip()

        try:
            port = int(self.port.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            self.log("Invalid port number")
            return

        try:
            server = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )
            server.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR, 1
            )
            server.bind((host, port))
            server.listen(5)
            server.settimeout(1)
        except OSError as error:
            self.log(f"Listener error: {error}")
            return

        self.server = server
        self.running = True

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        self.set_status("Status: Monitoring", "green")
        self.log(f"Listening on {host}:{port}")

        threading.Thread(
            target=self.accept_clients,
            daemon=True
        ).start()

    def accept_clients(self):
        while self.running:
            try:
                client, address = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            with self.lock:
                self.clients.add(client)

            self.log(f"Connected: {address[0]}:{address[1]}")

            threading.Thread(
                target=self.handle_client,
                args=(client, address),
                daemon=True
            ).start()

    def handle_client(self, client, address):
        try:
            client.settimeout(1)

            while self.running:
                try:
                    data = client.recv(4096)
                except socket.timeout:
                    continue

                if not data:
                    break

                message = data.decode(
                    "utf-8", errors="replace"
                )

                self.log(
                    f"{address[0]}: {message[:500]!r}"
                )

                client.sendall(b"Syntrix: Message received")

        except OSError as error:
            if self.running:
                self.log(f"Connection error: {error}")
        finally:
            with self.lock:
                self.clients.discard(client)

            client.close()
            self.log(f"Disconnected: {address[0]}")

    def stop_monitor(self):
        self.running = False

        if self.server:
            self.server.close()
            self.server = None

        with self.lock:
            clients = list(self.clients)

        for client in clients:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            client.close()

        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.set_status("Status: Offline", "gray")
        self.log("Monitoring stopped")

    def close_app(self):
        self.stop_monitor()
        self.destroy()


if __name__ == "__main__":
    app = Syntrix()
    app.mainloop()
