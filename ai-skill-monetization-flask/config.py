import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Defaults to a local SQLite file. To use MySQL instead, set DATABASE_URL, e.g.:
    #   mysql+pymysql://user:password@localhost:3306/skill_predictor
    # (and add PyMySQL to requirements.txt)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'skill_predictor.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
