import os
import logging
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    
    DEBUG = os.environ['FLASK_DEBUG'] == "1"
    SECRET_KEY = os.environ['SECRET_KEY']
    API_PASSWORD = os.environ['API_PASSWORD']
    USE_SQLITE = os.environ['USE_SQLITE'] == "True"

    HCAPTCHA_SITE_KEY = os.environ.get('HCAPTCHA_SITE_KEY') or ''
    HCAPTCHA_SECRET_KEY = os.environ.get('HCAPTCHA_SECRET_KEY') or ''
    HCAPTCHA_ENABLED = True if os.environ.get('HCAPTCHA_ENABLED') == "True" else False

    RATELIMIT_DEFAULT = "120 per minute, 20 per second"

    if USE_SQLITE:
        DB_NAME = os.environ['SQLITE_FILE']
        DB_URL = f"sqlite:///{os.path.join(basedir, DB_NAME)}"
        logging.info(f"App configured to use SQLite: {DB_URL}")

    else :
        DB_URL= os.environ['DATABASE_URI']
        print(f"Started up using DATABASE_URI")
        logging.info("App configured to use Production DATABASE_URI.")


    # APP CONFIG
    TIMEZONE = ZoneInfo('Asia/Kolkata') 
    
    AMOUNT_SHIRT = 1100
    AMOUNT_NOSHIRT = 900
    BOOTHS = ["T-SHIRT", "TIFFIN"]

    # Variables for Operational Commands
    GH_OWNER = os.environ.get("GH_OWNER")
    GH_REPO = os.environ.get("GH_REPO")
    GH_PAT = os.environ.get("GH_PAT")

    GCP_SA_KEY_B64=os.environ.get("GCP_SA_KEY_B64")
    REG_SHEET_KEY=os.environ.get("REG_SHEET_KEY")
    CR_PAY_SHEET_KEY=os.environ.get("CR_PAY_SHEET_KEY")
