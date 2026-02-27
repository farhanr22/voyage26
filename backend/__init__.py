import logging

from flask import Flask, session
import peewee
from playhouse.db_url import connect

from .config import Config
from . import models
from .models import db_proxy, Admins
from .extensions import login_manager, turnstile, limiter


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.debug and not app.testing:
        # Remove any handlers that might have added
        while app.logger.handlers:
            app.logger.removeHandler(app.logger.handlers[0])

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        
        # Stop the logger from propagating messages to the root logger to prevent duplicates
        app.logger.propagate = False
        
        app.logger.info('Voyage Admin application startup')

    # Initialize DB connection
    database_connection = connect(app.config["DB_URL"])
    db_proxy.initialize(database_connection)

    login_manager.init_app(app)
    turnstile.init_app(app)
    limiter.init_app(app)

    from .views.auth import auth_bp
    app.register_blueprint(auth_bp)

    from .views.main import main_bp
    app.register_blueprint(main_bp)

    from .views.registrations import registrations_bp
    app.register_blueprint(registrations_bp)

    from .views.cr_payments import cr_payments_bp
    app.register_blueprint(cr_payments_bp)

    from .views.booth import booth_bp
    app.register_blueprint(booth_bp)

    from .views.api import api_bp
    app.register_blueprint(api_bp)


    from . import cli
    cli.register_commands(app)

    from .ops import register_ops_commands
    register_ops_commands(app)
    
    
    from . import template_filters
    app.jinja_env.filters['datetimeformat'] = template_filters.format_datetime_simple


    @login_manager.user_loader
    def load_user(user_id):
        try:
            admin = Admins.get_by_id(user_id)
        except Admins.DoesNotExist:
            return None

        db_session_version = admin.session_version
        cookie_session_version = session.get("_session_version")

        # If the versions don't match, the session is invalid (version increments on password change)
        if db_session_version != cookie_session_version:
            return None

        return admin

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
        return {"db": models.db_proxy, "md": models}

    return app
