import os
import logging
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, ".env"))


class Config:

    DEBUG = os.environ["FLASK_DEBUG"] == "1"
    SECRET_KEY = os.environ["SECRET_KEY"]
    API_PASSWORD = os.environ["API_PASSWORD"]
    USE_SQLITE = os.environ["USE_SQLITE"] == "True"

    # Cloudflare Turnstile Setup
    TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY") or ""
    TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY") or ""
    TURNSTILE_ENABLED = True if os.environ.get("TURNSTILE_ENABLED") == "True" else False

    RATELIMIT_DEFAULT = "120 per minute, 20 per second"

    if USE_SQLITE:
        DB_NAME = os.environ["SQLITE_FILE"]
        DB_URL = f"sqlite:///{os.path.join(basedir, DB_NAME)}"
        logging.info(f"App configured to use SQLite: {DB_URL}")

    else:
        DB_URL = os.environ["DATABASE_URI"]
        logging.info("App configured to use Production DATABASE_URI.")

    # APP CONFIG
    TIMEZONE = ZoneInfo("Asia/Kolkata")

    AMOUNT_SHIRT = 1200
    AMOUNT_NOSHIRT = 1000
    BOOTHS = ["T-SHIRT", "TIFFIN"]

    # Variables for Operational Commands
    GH_OWNER = os.environ.get("GH_OWNER")
    GH_REPO = os.environ.get("GH_REPO")
    GH_PAT = os.environ.get("GH_PAT")

    # Tally API Configuration
    TALLY_API_KEY = os.environ.get("TALLY_API_KEY")
    TALLY_REGISTRATION_FORM_ID = os.environ.get("TALLY_REGISTRATION_FORM_ID")
    TALLY_CR_FORM_ID = os.environ.get("TALLY_CR_FORM_ID")
