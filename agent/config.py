import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

def get_base_dir() -> str:
    # when running as bundled .exe via PyInstaller
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    # when running as normal python script
    return str(Path(__file__).resolve().parent.parent)

BASE_DIR = get_base_dir()
BACKEND_URL = "https://uncommonhacks-agra-production.up.railway.app"

@dataclass
class AgentConfig:
    watch_dirs: List[str] = field(
        default_factory=lambda: [
            str(Path.home() / "Downloads"),
            str(Path.home() / "Desktop"),
            "C:/watched_folder"
        ]
    )
    scan_extensions: List[str] = field(
        default_factory=lambda: [
            ".exe", ".dll", ".sys", ".ps1", ".bat",
            ".xlsm", ".pdf", ".elf", ".apk",
            ".com", ".txt", ".zip",
        ]
    )
    scan_interval_seconds: float = 2.0
    threat_threshold: int = 70
    warning_threshold: int = 40
    max_file_size_mb: int = 100
    backend_url: str = BACKEND_URL
    model_dir: str = field(default_factory=lambda: os.path.join(BASE_DIR, "model"))
    use_llm: bool = True
    ollama_model: str = "qwen2.5:0.5b"
    ollama_url: str = "http://127.0.0.1:11434"
