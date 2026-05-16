# AGRA - AI-Powered Endpoint Detection & Response

AGRA is a lightweight EDR agent that monitors your filesystem for new files, scores them using ML models trained on the [EMBER2024](https://github.com/FutureComputing4AI/EMBER2024) dataset, enriches findings with a locally-hosted LLM (Qwen 2.5 0.5B via Ollama), and displays results on a real-time React dashboard.

## Architecture

```
File dropped in ~/Downloads
        |
   [watchdog event]
        |
   Feature extraction (thrember / heuristic fallback)
        |
   ML scoring (LightGBM + Random Forest ensemble)
        |
   Clustering (KMeans + HDBSCAN)
        |
   LLM analysis (Qwen 2.5 0.5B via Ollama)
        |
   SQLite storage + FastAPI backend
        |
   React dashboard (real-time polling)
```

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **Ollama** (for local LLM analysis)

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/SaiKamalaksha/UncommonHacks-Agra.git
cd UncommonHacks-Agra
```

### 2. Install Python dependencies

```bash
pip install fastapi uvicorn watchdog lightgbm scikit-learn hdbscan requests numpy onnxruntime
```

### 3. Install thrember (EMBER2024 feature extractor)

`thrember` is not on PyPI -- install it from the EMBER2024 repo:

```bash
git clone https://github.com/FutureComputing4AI/EMBER2024.git
cd EMBER2024
pip install .
cd ..
```

### 4. Install and start Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the Qwen model (~400MB)
ollama pull qwen2.5:0.5b

# Start the Ollama server (if not already running)
ollama serve
```

> If you skip this step, AGRA still works in ML-only mode -- you just won't get LLM-generated threat descriptions.

### 5. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 6. Run the pipeline

```bash
python pipeline.py
```

This single command starts:
- The FastAPI backend on `http://127.0.0.1:8000`
- The file watcher on `~/Downloads`
- The ML scoring engine (with ONNX acceleration if available)
- The LLM analyst (connects to Ollama)

### 7. Start the dashboard (separate terminal)

```bash
cd frontend
npm run dev
```

Open the URL shown by Vite (usually `http://localhost:5173`).

### 8. Test it

Download the [EICAR test file](https://www.eicar.org/download-anti-malware-testfile/) -- AGRA should detect it within seconds and display the alert on the dashboard. Malicious files are automatically deleted.

## CLI Options

```
python pipeline.py --watch ~/Downloads ~/Desktop   # watch multiple directories
python pipeline.py --port 9000                      # change API port
python pipeline.py --no-llm                         # disable LLM, ML-only mode
python pipeline.py --no-npu                         # disable ONNX acceleration
```

## Project Structure

```
UncommonHacks-Agra/
├── pipeline.py              # All-in-one EDR pipeline (main entrypoint)
├── model/
│   ├── lgbm_classifier.model      # Trained LightGBM model
│   ├── random_forest_classifier.pkl # Trained Random Forest model
│   ├── kmeans_clusterer.pkl        # KMeans clustering model
│   ├── hdbscan_clusterer.pkl       # HDBSCAN clustering model
│   ├── cluster_scaler.pkl          # Feature scaler for clustering
│   ├── cluster_pca.pkl             # PCA for dimensionality reduction
│   ├── lgbm_classifier.onnx       # ONNX-optimized LightGBM (~232x faster)
│   ├── random_forest_classifier.onnx # ONNX-optimized Random Forest
│   └── convert_onnx.py            # Script to regenerate ONNX models
├── frontend/
│   ├── src/
│   │   ├── Dashboard.jsx           # Main dashboard with live alert feed
│   │   ├── App.jsx                 # App router with Firebase auth
│   │   ├── Auth.jsx                # Login/signup page
│   │   └── firebase.js             # Firebase config
│   └── package.json
├── agent/                   # Modular agent (alternative to pipeline.py)
│   ├── main.py
│   ├── agent.py
│   ├── scorer.py
│   ├── alerter.py
│   ├── llm_analyst.py
│   └── config.py
├── backend/                 # Modular backend (alternative to pipeline.py)
│   ├── app.py
│   ├── database.py
│   └── models.py
└── README.md
```

## How It Works

1. **File Detection** -- Watchdog monitors configured directories for new, modified, or renamed files
2. **Feature Extraction** -- Uses `thrember` (EMBER2024) to extract a 2568-dimensional feature vector from binaries. Falls back to heuristic extraction for non-PE files
3. **ML Scoring** -- LightGBM and Random Forest classifiers produce independent malware probabilities, blended 70/30 into a 0-100 threat score
4. **Clustering** -- KMeans and HDBSCAN assign cluster IDs to group similar threats
5. **LLM Analysis** -- Sends ML findings to Qwen 2.5 0.5B (via Ollama) for a human-readable threat assessment
6. **Alert & Response** -- Results are stored in SQLite, served via FastAPI, and displayed on the React dashboard. Files scoring above 70 are automatically deleted

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/alerts?limit=50` | Recent alerts |
| `POST` | `/api/alerts` | Create alert (used by agent) |
| `GET` | `/api/stats` | Aggregated scan statistics |

## Tech Stack

- **ML**: LightGBM, scikit-learn, HDBSCAN, ONNX Runtime
- **LLM**: Qwen 2.5 0.5B via Ollama
- **Backend**: FastAPI, SQLite, Uvicorn
- **Frontend**: React 19, Vite 7, Tailwind CSS 4
- **Auth**: Firebase
- **File Monitoring**: Watchdog
- **Feature Extraction**: thrember (EMBER2024)

## License

Built at UncommonHacks 2025.
