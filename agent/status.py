import tempfile
from datetime import datetime
from html import escape
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


class StatusStore:
    def __init__(self) -> None:
        self.lock = Lock()
        self.mode_label = "unknown"
        self.npu_available = False
        self.last_scans: List[Dict[str, Any]] = []

    def update_mode(self, mode_label: str) -> None:
        with self.lock:
            self.mode_label = mode_label
            self.npu_available = mode_label.lower().startswith("intel")

    def record_scan(self, result: Any, deleted: bool, alert_sent: bool) -> None:
        with self.lock:
            self.last_scans.insert(0, {
                "timestamp": result.timestamp,
                "filename": result.filename,
                "filepath": result.filepath,
                "score": result.threat_score,
                "classification": result.classification,
                "deleted": deleted,
                "alert_sent": alert_sent,
                "llm_analysis": result.llm_analysis or "",
            })
            self.last_scans = self.last_scans[:20]

    def write_status_page(self) -> Path:
        path = Path(tempfile.gettempdir()) / "agra_agent_status.html"
        path.write_text(self._render_html(), encoding="utf-8")
        return path

    def _render_html(self) -> str:
        with self.lock:
            mode_label = escape(self.mode_label)
            npu_status = "Active" if self.npu_available else "Not active"
            entries = list(self.last_scans)

        rows = []
        for item in entries:
            rows.append(
                "<tr>"
                f"<td>{escape(item['timestamp'])}</td>"
                f"<td>{escape(item['filename'])}</td>"
                f"<td>{escape(item['filepath'])}</td>"
                f"<td>{item['score']}</td>"
                f"<td>{escape(item['classification'])}</td>"
                f"<td>{'Deleted' if item['deleted'] else 'Kept'}</td>"
                f"<td>{'Yes' if item['alert_sent'] else 'No'}</td>"
                f"<td>{escape(item['llm_analysis'])}</td>"
                "</tr>"
            )

        rows_html = "\n".join(rows) if rows else (
            "<tr><td colspan='8'>No scans processed yet.</td></tr>"
        )

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>AGRA Agent Status</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #121212; color: #eee; margin: 0; padding: 20px; }}
    h1, h2 {{ color: #ffd700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ padding: 8px 10px; border: 1px solid #333; text-align: left; }}
    th {{ background: #1f1f1f; }}
    tr:nth-child(even) {{ background: #181818; }}
    .summary {{ display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
    .card {{ background: #1e1e1e; border: 1px solid #333; padding: 14px; border-radius: 8px; }}
    .note {{ margin-top: 14px; color: #bbb; }}
  </style>
</head>
<body>
  <h1>AGRA Agent Status</h1>
  <div class="summary">
    <div class="card"><strong>ONNX/OpenVINO mode</strong><div>{mode_label}</div></div>
    <div class="card"><strong>NPU access</strong><div>{npu_status}</div></div>
    <div class="card"><strong>Generated</strong><div>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></div>
  </div>
  <p class="note">This local info panel shows recent files that were scanned and whether they were deleted. "NPU access" indicates whether the agent is using an Intel accelerated mode; it does not directly change hardware frequency.</p>
  <h2>Recent scans</h2>
  <table>
    <thead>
      <tr>
        <th>Time</th><th>File</th><th>Path</th><th>Score</th><th>Class</th><th>Action</th><th>Alert sent</th><th>LLM summary</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>
""".strip()
