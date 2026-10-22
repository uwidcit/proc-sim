from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()


def get_migrate(app):
    return Migrate(app, db)


def create_db():
    """Create tables for tests/local bootstrap. Prefer `flask db upgrade` in prod."""
    db.create_all()


def init_db(app):
    db.init_app(app)
