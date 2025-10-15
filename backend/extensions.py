from flask_login import LoginManager
from flask_hcaptcha import hCaptcha
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

hcaptcha = hCaptcha()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://" # Default for development, will be overridden by config
)