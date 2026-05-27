"""
Configuration management for DuckDB Analytics Layer.
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── Base Paths ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "raw").mkdir(exist_ok=True)
(DATA_DIR / "processed").mkdir(exist_ok=True)
(DATA_DIR / "reports").mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── PostgreSQL Configuration ──────────────────────────────────────────
POSTGRES_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "weather_db"),
    "user":     os.getenv("POSTGRES_USER", "weather_user"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

POSTGRES_URL = (
    f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
    f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}"
    f"/{POSTGRES_CONFIG['database']}"
)

# ── DuckDB Configuration ──────────────────────────────────────────────
DUCKDB_PATH = os.getenv("DUCKDB_PATH", str(DATA_DIR / "weather_analytics.duckdb"))

# ── Analytics Configuration ───────────────────────────────────────────
ANALYTICS_SCHEDULE_INTERVAL = int(os.getenv("ANALYTICS_SCHEDULE_INTERVAL", "3600"))
ANALYTICS_LOOKBACK_DAYS = int(os.getenv("ANALYTICS_LOOKBACK_DAYS", "30"))

# ── Export Configuration ──────────────────────────────────────────────
PARQUET_OUTPUT_DIR = os.getenv("PARQUET_OUTPUT_DIR", str(DATA_DIR / "processed"))
REPORTS_OUTPUT_DIR = os.getenv("REPORTS_OUTPUT_DIR", str(DATA_DIR / "reports"))

# ── Logging Configuration ─────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "analytics.log"))

# ── Cities tracked in Projects 1 and 2 ───────────────────────────────
TRACKED_CITIES = [
    "Paris", "London", "New York", "Tokyo", "Douala",
    "Berlin", "Lagos", "Sydney", "Nairobi", "São Paulo",
    "Dubai", "Mumbai"
]