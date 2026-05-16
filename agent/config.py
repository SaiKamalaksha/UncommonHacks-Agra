import os

# User
USERNAME = os.getlogin()

# Watched paths
WATCHED_PATHS = [
    f"C:/Users/{USERNAME}/Downloads",
    f"C:/Users/{USERNAME}/Desktop",
    "C:/watched_folder"
]

# File types to scan
WATCHED_EXTENSIONS = [".exe", ".dll", ".msi", ".bat", ".ps1"]

# Scoring thresholds
MALICIOUS_THRESHOLD = 0.7
SUSPICIOUS_THRESHOLD = 0.4

# Backend
BACKEND_URL = "http://localhost:5000"

# App
APP_NAME = "Agra Security"
VERSION = "0.1.0"