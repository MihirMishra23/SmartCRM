from flask import Flask
from flask_cors import CORS
from .config import Config
from .models.base import db
from .api.routes import api


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(api, resources={r"/*": {"origins": "http://localhost:5173"}})

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(api, url_prefix="/api")

    return app
