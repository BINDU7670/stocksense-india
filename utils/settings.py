from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# 🔹 Load .env file
load_dotenv()

# 🔹 Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
REPORTS_DIR = DATA_DIR / "reports"
GRAPH_DIR = DATA_DIR / "graph"

# 🔹 Environment variables
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus:free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# 🔹 Ensure folders exist
def ensure_directories() -> None:
    for directory in (DATA_DIR, RAW_DATA_DIR, REPORTS_DIR, GRAPH_DIR):
        directory.mkdir(parents=True, exist_ok=True)