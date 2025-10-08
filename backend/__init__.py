# __init__.py
from flask import Flask
import peewee
from playhouse.db_url import connect

from .config import Config
from . import models
from .models import db_proxy 


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize DB connection
    database_connection = connect(app.config['DB_URL'])
    db_proxy.initialize(database_connection)

    # --- Request Hooks ---
    @app.before_request
    def before_request():
        db_proxy.connect(reuse_if_open=True)

    @app.after_request
    def after_request(response):
        db_proxy.close()
        return response

    # --- Shell Context ---
    @app.shell_context_processor
    def make_shell_context():
        return {
            "db": models.db_proxy,
            "md": models
        }

    return app