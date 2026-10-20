import os


def _normalize_database_url(url: str) -> str:
    # Heroku / some hosts still emit postgres://; SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _resolve_database_uri() -> str:
    for key in ("DATABASE_URL", "SQLALCHEMY_DATABASE_URI"):
        value = os.environ.get(key)
        if value:
            return _normalize_database_url(value)
    return "sqlite:///temp-database.db"


SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-use-env-in-prod")
ENV = os.environ.get("ENV", "development")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")
