import requests
from agent.auth import DUMMY_EMAIL, DUMMY_PASSWORD, DUMMY_TOKEN, BACKEND_URL

try:
    import tkinter as tk
except ModuleNotFoundError:
    tk = None

class LoginWindow:
    def __init__(self):
        self.token = None
        self.root = None
        if tk is None:
            print("[AUTH] Tkinter is not available; using dummy test login.")
            return

        self.root = tk.Tk()
        self.root.title("Agra Security — Login")
        self.root.geometry("360x240")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f0f0f")
        self.root.attributes("-topmost", True)
        self._center_window()
        self._build_ui()

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (360 // 2)
        y = (self.root.winfo_screenheight() // 2) - (240 // 2)
        self.root.geometry(f"360x240+{x}+{y}")

    def _build_ui(self):
        tk.Label(
            self.root, text="🛡️ Agra Security",
            font=("Helvetica", 16, "bold"),
            bg="#0f0f0f", fg="white"
        ).pack(pady=(20, 4))

        tk.Label(
            self.root, text="Sign in to activate protection",
            font=("Helvetica", 9),
            bg="#0f0f0f", fg="#888888"
        ).pack(pady=(0, 16))

        self.email_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        tk.Entry(
            self.root, textvariable=self.email_var,
            font=("Helvetica", 11),
            width=28, bg="#1e1e1e", fg="white",
            insertbackground="white",
            relief="flat"
        ).pack(pady=4)

        tk.Entry(
            self.root, textvariable=self.pass_var,
            font=("Helvetica", 11),
            width=28, bg="#1e1e1e", fg="white",
            insertbackground="white",
            show="*", relief="flat"
        ).pack(pady=4)

        self.error_label = tk.Label(
            self.root, text="",
            font=("Helvetica", 9),
            bg="#0f0f0f", fg="#ff5555"
        )
        self.error_label.pack(pady=2)

        tk.Button(
            self.root, text="Login",
            font=("Helvetica", 11, "bold"),
            bg="#00c853", fg="black",
            relief="flat", width=26,
            command=self._login
        ).pack(pady=8)

        # bind enter key
        self.root.bind("<Return>", lambda e: self._login())

    def _login(self):
        email = self.email_var.get().strip()
        password = self.pass_var.get().strip()

        if not email or not password:
            self.error_label.config(text="Please enter email and password")
            return

        # TEMP: dummy login bypass
        if email == DUMMY_EMAIL and password == DUMMY_PASSWORD:
            print("[AUTH] Dummy login successful")
            self.token = DUMMY_TOKEN
            self.root.destroy()
            return

        # real backend login
        try:
            response = requests.post(
                f"{BACKEND_URL}/login",
                json={"email": email, "password": password},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.root.destroy()
            else:
                self.error_label.config(text="Invalid credentials")
        except Exception as e:
            self.error_label.config(text="Could not connect to server")
            print(f"[AUTH ERROR] {e}")

    def run(self) -> str:
        if self.root is None:
            return DUMMY_TOKEN

        self.root.mainloop()
        return self.token
