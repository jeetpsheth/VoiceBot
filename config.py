"""Load config from environment."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Challenge test number
TEST_NUMBER = os.getenv("TEST_NUMBER", "+18054398008")

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"
BUGS_DIR = PROJECT_ROOT / "bug_reports"

for d in (TRANSCRIPTS_DIR, RECORDINGS_DIR, BUGS_DIR):
    d.mkdir(parents=True, exist_ok=True)
