import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("REDPEN_MODEL", "gemini-3.5-flash").strip()
# tried in order when the main model 404s or its quota runs out
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("REDPEN_FALLBACK_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite").split(",")
    if m.strip()
]
# cheap, fast model for high-volume calls (simulated students, claim extraction, probe planning)
FAST_MODEL = os.getenv("REDPEN_FAST_MODEL", "gemini-3.5-flash-lite").strip()
EMBED_MODEL =os.getenv("REDPEN_EMBED_MODEL", "gemini-embedding-001").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()

DATA_DIR = Path(os.getenv("REDPEN_DATA_DIR", ROOT / "data"))
PROMPTS_DIR = ROOT / "prompts"
STATIC_DIR = ROOT / "static"

LESSON_MINUTES = 45
MIN_LESSON_MINUTES = 38
USER_AGENT = "redpen/0.1 (https://github.com/redpen-lessons/redpen; lesson research tool) httpx/0.28"
HTTP_TIMEOUT = 12
EXEC_TIMEOUT = 15
