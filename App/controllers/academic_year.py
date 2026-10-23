"""Academic year scoping for procurement runs."""
from flask import session

from App.academic_years import (
    ACADEMIC_YEARS,
    DEFAULT_ACADEMIC_YEAR,
    SESSION_KEY,
)


def get_academic_years():
    return list(ACADEMIC_YEARS)


def is_valid_year(year):
    try:
        return int(year) in ACADEMIC_YEARS
    except (TypeError, ValueError):
        return False


def get_active_year():
    """Platform current year (persisted in Settings; used by students)."""
    try:
        from App.controllers.settings import get_active_academic_year

        return get_active_academic_year()
    except Exception:
        return DEFAULT_ACADEMIC_YEAR


def _admin_preview_year():
    """Session-only year for admin record browsing, if an admin is logged in."""
    try:
        from flask_jwt_extended import verify_jwt_in_request, current_user

        verify_jwt_in_request(optional=True)
        user = current_user
        if not user or not user.is_admin():
            return None
        preview = session.get(SESSION_KEY)
        if is_valid_year(preview):
            return int(preview)
    except Exception:
        return None
    return None


def get_current_year():
    """
    Data-scope year for admin screens: sidebar preview if set, else platform year.
    Students always resolve to the platform active year (no preview session).
    """
    preview = _admin_preview_year()
    if preview is not None:
        return preview
    return get_active_year()


def set_admin_view_year(year):
    """Admin sidebar: preview another year's records (session only)."""
    year = int(year)
    if year not in ACADEMIC_YEARS:
        return None
    session[SESSION_KEY] = year
    return year


def set_current_year(year):
    """Settings: set the platform current year for all students (persisted)."""
    year = int(year)
    if year not in ACADEMIC_YEARS:
        return None
    from App.controllers.settings import set_active_academic_year

    settings, err = set_active_academic_year(year)
    if err or not settings:
        return None
    return year
