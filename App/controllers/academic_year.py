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
    """Platform current year (persisted; used by students and admin)."""
    try:
        from App.controllers.settings import get_active_academic_year

        return get_active_academic_year()
    except Exception:
        return DEFAULT_ACADEMIC_YEAR


def get_current_year():
    """Data scope year — always the admin-configured current year."""
    return get_active_year()


def set_current_year(year):
    """Set the current academic year for everyone (persisted + session)."""
    year = int(year)
    if year not in ACADEMIC_YEARS:
        return None
    from App.controllers.settings import set_active_academic_year

    settings, err = set_active_academic_year(year)
    if err or not settings:
        return None
    try:
        session[SESSION_KEY] = year
    except RuntimeError:
        pass
    return year
