import os
from datetime import timedelta


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def load_config(app, overrides):
    if os.path.exists(os.path.join("./App", "custom_config.py")):
        app.config.from_object("App.custom_config")
    else:
        app.config.from_object("App.default_config")

    app.config.from_prefixed_env()

    # Prefer explicit DATABASE_URL (EasyPanel / Compose) over prefixed FLASK_ vars.
    database_url = os.environ.get("DATABASE_URL") or app.config.get("SQLALCHEMY_DATABASE_URI")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_database_url(database_url)

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["PREFERRED_URL_SCHEME"] = "https"
    app.config["UPLOADED_PHOTOS_DEST"] = "App/uploads"
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token"
    app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
    app.config["JWT_COOKIE_SECURE"] = True
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    app.config["JWT_CSRF_CHECK_FORM"] = True
    app.config["JWT_CSRF_IN_COOKIES"] = True
    # Default flask-jwt-extended expiry is 15 minutes; keep sessions usable for lab work
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["FLASK_ADMIN_SWATCH"] = "darkly"

    for key in overrides:
        app.config[key] = overrides[key]

    # Allow insecure cookies in testing / local sqlite without HTTPS
    env = (app.config.get("ENV") or os.environ.get("ENV") or "").lower()
    if app.config.get("TESTING") or env in ("development", "dev", "local"):
        app.config["JWT_COOKIE_SECURE"] = False
    if app.config.get("TESTING"):
        app.config["JWT_COOKIE_CSRF_PROTECT"] = False
