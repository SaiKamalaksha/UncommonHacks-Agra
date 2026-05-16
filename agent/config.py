from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class AgentConfig:
    watch_dirs: List[str] = field(
        default_factory=lambda: [str(Path.home() / "Downloads")]
    )
    scan_extensions: List[str] = field(
        default_factory=lambda: [
            ".exe", ".dll", ".sys", ".ps1", ".bat",
            ".xlsm", ".pdf", ".elf", ".apk",
        ]
    )
    scan_interval_seconds: float = 2.0
    threat_threshold: int = 70
    warning_threshold: int = 40
    max_file_size_mb: int = 100

    backend_url: str = "http://127.0.0.1:8000"
    model_dir: str = str(Path(__file__).resolve().parent.parent / "model")

    use_llm: bool = True
    ollama_model: str = "qwen2.5:0.5b"
    ollama_url: str = "http://127.0.0.1:11434"
