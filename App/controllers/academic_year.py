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


def get_current_year():
    try:
        year = session.get(SESSION_KEY)
    except RuntimeError:
        # Outside a request context (CLI / initialize)
        return DEFAULT_ACADEMIC_YEAR
    if is_valid_year(year):
        return int(year)
    session[SESSION_KEY] = DEFAULT_ACADEMIC_YEAR
    return DEFAULT_ACADEMIC_YEAR


def set_current_year(year):
    year = int(year)
    if year not in ACADEMIC_YEARS:
        return None
    session[SESSION_KEY] = year
    return year
