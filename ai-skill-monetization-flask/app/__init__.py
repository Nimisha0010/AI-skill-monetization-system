import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, instance_relative_config=False)

    from config import Config
    app.config.from_object(Config)

    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance"), exist_ok=True)

    db.init_app(app)

    with app.app_context():
        from . import models  # noqa: F401  (register models before create_all)
        db.create_all()
        from .data import seed_catalog
        seed_catalog()

        from .routes import bp
        app.register_blueprint(bp)

    return app
