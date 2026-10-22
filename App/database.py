from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import inspect, text

from App.academic_years import DEFAULT_ACADEMIC_YEAR


db = SQLAlchemy()

def get_migrate(app):
    return Migrate(app, db)

def create_db():
    db.create_all()
    ensure_schema_columns()


def ensure_schema_columns():
    """Add newer columns to existing tables if missing."""
    try:
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
    except Exception:
        return
    altered = False

    def _add(table, column_sql):
        nonlocal altered
        if table not in tables:
            return
        columns = {col["name"] for col in inspector.get_columns(table)}
        col_name = column_sql.split()[0]
        if col_name in columns:
            return
        quoted = f'"{table}"' if table == "group" else table
        db.session.execute(text(f"ALTER TABLE {quoted} ADD COLUMN {column_sql}"))
        altered = True

    _add("group", f"academic_year INTEGER NOT NULL DEFAULT {DEFAULT_ACADEMIC_YEAR}")
    _add("lot", f"academic_year INTEGER NOT NULL DEFAULT {DEFAULT_ACADEMIC_YEAR}")
    _add("lot", "numMachines INTEGER NOT NULL DEFAULT 0")
    _add("bid", "message TEXT NOT NULL DEFAULT ''")
    _add(
        "app_setting",
        f"active_academic_year INTEGER NOT NULL DEFAULT {DEFAULT_ACADEMIC_YEAR}",
    )
    _add(
        "student",
        f"academic_year INTEGER NOT NULL DEFAULT {DEFAULT_ACADEMIC_YEAR}",
    )
    # Postgres requires TRUE/FALSE for boolean defaults (not 0/1)
    _add("app_setting", "results_published BOOLEAN NOT NULL DEFAULT FALSE")
    # Existing students are treated as already claimed
    _add("student", "account_claimed BOOLEAN NOT NULL DEFAULT TRUE")

    if altered:
        db.session.commit()


def init_db(app):
    db.init_app(app)
    with app.app_context():
        ensure_schema_columns()
