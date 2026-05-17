import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import messagebox
import requests
from auth import DUMMY_EMAIL, DUMMY_PASSWORD, DUMMY_TOKEN, BACKEND_URL

class LoginWindow:
    def __init__(self):
        self.token = None
        self.root = tk.Tk()
        self.root.title("Agra Security — Login")
        self.root.geometry("360x260")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f0f0f")
        self.root.attributes("-topmost", True)
        self._center_window()
        self._build_ui()

    def _center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (360 // 2)
        y = (self.root.winfo_screenheight() // 2) - (260 // 2)
        self.root.geometry(f"360x260+{x}+{y}")

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
        ).pack(pady=(0, 12))

        self.email_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        tk.Label(self.root, text="Email", font=("Helvetica", 9),
                 bg="#0f0f0f", fg="#aaaaaa").pack(anchor="w", padx=40)
        tk.Entry(
            self.root, textvariable=self.email_var,
            font=("Helvetica", 11),
            width=28, bg="#1e1e1e", fg="white",
            insertbackground="white", relief="flat"
        ).pack(pady=(2, 8), padx=40)

        tk.Label(self.root, text="Password", font=("Helvetica", 9),
                 bg="#0f0f0f", fg="#aaaaaa").pack(anchor="w", padx=40)
        tk.Entry(
            self.root, textvariable=self.pass_var,
            font=("Helvetica", 11),
            width=28, bg="#1e1e1e", fg="white",
            insertbackground="white",
            show="*", relief="flat"
        ).pack(pady=(2, 8), padx=40)

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

        tk.Label(
            self.root,
            text="Register at agra-dashboard.vercel.app",
            font=("Helvetica", 8),
            bg="#0f0f0f", fg="#555555"
        ).pack(pady=(0, 4))

        self.root.bind("<Return>", lambda e: self._login())

    def _login(self):
        email = self.email_var.get().strip()
        password = self.pass_var.get().strip()

        if not email or not password:
            self.error_label.config(text="Please enter email and password")
            return

        # dummy bypass for testing
        if email == DUMMY_EMAIL and password == DUMMY_PASSWORD:
            print("[AUTH] Dummy login successful")
            self.token = DUMMY_TOKEN
            self.root.destroy()
            return

        # real Railway backend login
        try:
            response = requests.post(
                f"{BACKEND_URL}/login",
                json={"email": email, "password": password},
                timeout=5
            )
            if response.status_code == 200:
                self.token = response.json().get("token")
                print(f"[AUTH] Login successful: {email}")
                self.root.destroy()
            else:
                self.error_label.config(
                    text="Invalid credentials — register at the dashboard first"
                )
        except Exception as e:
            self.error_label.config(text="Could not connect to server")
            print(f"[AUTH ERROR] {e}")

    def run(self) -> str:
        self.root.mainloop()
        return self.token