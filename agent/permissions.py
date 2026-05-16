import os
import sys
import ctypes

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    if not is_admin():
        print("[PERMISSIONS] Requesting admin privileges...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

def check_folder_access() -> bool:
    username = os.getlogin()
    paths = [
        f"C:/Users/{username}/Downloads",
        f"C:/Users/{username}/Desktop"
    ]
    all_good = True
    for path in paths:
        if os.access(path, os.R_OK):
            print(f"[PERMISSIONS] Access granted: {path}")
        else:
            print(f"[PERMISSIONS] Access denied: {path}")
            all_good = False
    return all_good