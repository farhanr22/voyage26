import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

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
        print(f"Started up using SQLITE : {DB_URL}")
    else :
        DB_URL= os.environ['DATABASE_URI']
        print(f"Started up using DATABASE_URI")



    # ---- APP CONFIG ----
    TIMEZONE = ZoneInfo('Asia/Kolkata') 
    
    AMOUNT_SHIRT = 1100
    AMOUNT_NOSHIRT = 900
    BOOTHS = ["T-SHIRT", "TIFFIN"]