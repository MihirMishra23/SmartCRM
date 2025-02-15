from flask import Flask
from flask_cors import CORS
from .config import Config
from .models.base import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app)

    # Register blueprints
    from .api.routes import api

    app.register_blueprint(api, url_prefix="/api")

    return app
