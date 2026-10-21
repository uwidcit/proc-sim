import os
import warnings

# Flask-Admin 1.x still imports pkg_resources; silence Setuptools deprecation noise
warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API.*",
    category=UserWarning,
    module=r"flask_admin\.contrib",
)

import os

from flask import Flask, render_template
from flask_uploads import DOCUMENTS, IMAGES, TEXT, UploadSet, configure_uploads
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from App.database import init_db
from App.config import load_config
from App.controllers import setup_jwt, add_auth_context
from App.views import views, setup_admin


def add_views(app):
    for view in views:
        app.register_blueprint(view)


def create_app(overrides=None):
    overrides = overrides or {}
    app = Flask(__name__, static_url_path="/static")
    load_config(app, overrides)

    # EasyPanel / reverse proxies terminate TLS; trust X-Forwarded-* headers.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    cors_origins = app.config.get("CORS_ORIGINS")
    if cors_origins:
        CORS(app, origins=[o.strip() for o in cors_origins.split(",") if o.strip()])
    else:
        CORS(app, supports_credentials=True)

    add_auth_context(app)

    from App.utils import format_money, CURRENCY_CODE

    app.jinja_env.filters["money"] = format_money

    @app.context_processor
    def inject_currency():
        return dict(currency_code=CURRENCY_CODE)

    @app.context_processor
    def inject_csrf():
        try:
            from flask import request as flask_request

            token = flask_request.cookies.get("csrf_access_token")
            return dict(csrf_token=token or "")
        except Exception:
            return dict(csrf_token="")

    @app.context_processor
    def inject_academic_year():
        try:
            from App.controllers.academic_year import (
                get_academic_years,
                get_current_year,
                get_active_year,
            )

            return dict(
                academic_years=get_academic_years(),
                current_academic_year=get_current_year(),
                active_academic_year=get_active_year(),
            )
        except Exception:
            from App.academic_years import ACADEMIC_YEARS, DEFAULT_ACADEMIC_YEAR

            return dict(
                academic_years=list(ACADEMIC_YEARS),
                current_academic_year=DEFAULT_ACADEMIC_YEAR,
                active_academic_year=DEFAULT_ACADEMIC_YEAR,
            )

    upload_dir = app.config.get("UPLOADED_PHOTOS_DEST", "App/uploads")
    os.makedirs(upload_dir, exist_ok=True)
    photos = UploadSet("photos", TEXT + DOCUMENTS + IMAGES)
    configure_uploads(app, photos)

    add_views(app)
    init_db(app)
    jwt = setup_jwt(app)
    setup_admin(app)

    @jwt.invalid_token_loader
    @jwt.unauthorized_loader
    def custom_unauthorized_response(error):
        return render_template("401.html", error=error), 401

    app.app_context().push()
    return app