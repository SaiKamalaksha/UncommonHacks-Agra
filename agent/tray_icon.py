from PIL import Image, ImageDraw
import pystray
import webbrowser
from agent.config import BACKEND_URL

def create_icon(color="green"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.polygon([
        (32, 4),
        (60, 16),
        (60, 36),
        (32, 60),
        (4, 36),
        (4, 16),
    ], fill=color)
    return img

def build_tray(observer, stats: dict):
    def on_quit(icon, item):
        print("[AGRA] Shutting down...")
        observer.stop()
        icon.stop()

    def open_dashboard(icon, item):
        webbrowser.open(f"{BACKEND_URL}/dashboard")

    icon = pystray.Icon(
        name="AgraSecurity",
        icon=create_icon("green"),
        title="Agra Security — Protected",
        menu=pystray.Menu(
            pystray.MenuItem(
                lambda text: f"🛡️ {stats['blocked']} threats blocked",
                None,
                enabled=False
            ),
            pystray.MenuItem("Open Dashboard", open_dashboard),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit)
        )
    )
    return icon
