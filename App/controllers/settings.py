from App.models import AppSetting
from App.database import db
from App.academic_years import DEFAULT_ACADEMIC_YEAR, ACADEMIC_YEARS


def get_or_create_settings():
    settings = db.session.scalars(db.select(AppSetting)).first()
    if not settings:
        settings = AppSetting(
            group_size_min=3,
            group_size_max=3,
            active_academic_year=DEFAULT_ACADEMIC_YEAR,
            results_published=False,
        )
        db.session.add(settings)
        db.session.commit()
        return settings

    dirty = False
    if getattr(settings, "active_academic_year", None) is None:
        settings.active_academic_year = DEFAULT_ACADEMIC_YEAR
        dirty = True
    if getattr(settings, "results_published", None) is None:
        settings.results_published = False
        dirty = True
    if dirty:
        db.session.commit()
    return settings


def get_group_size_range():
    settings = get_or_create_settings()
    return settings.group_size_min, settings.group_size_max


def get_active_academic_year():
    settings = get_or_create_settings()
    year = settings.active_academic_year
    if year in ACADEMIC_YEARS:
        return int(year)
    return DEFAULT_ACADEMIC_YEAR


def set_active_academic_year(year):
    year = int(year)
    if year not in ACADEMIC_YEARS:
        return None, "Invalid academic year"
    settings = get_or_create_settings()
    settings.active_academic_year = year
    db.session.commit()
    return settings, None


def are_results_published():
    return bool(get_or_create_settings().results_published)


def set_results_published(published):
    settings = get_or_create_settings()
    settings.results_published = bool(published)
    db.session.commit()
    return settings


def update_settings(min_size, max_size, active_year=None, results_published=None):
    min_size = int(min_size)
    max_size = int(max_size)
    if min_size < 1 or max_size < min_size:
        return None, "Invalid group size range"
    settings = get_or_create_settings()
    settings.group_size_min = min_size
    settings.group_size_max = max_size
    if active_year is not None:
        year = int(active_year)
        if year not in ACADEMIC_YEARS:
            return None, "Invalid academic year"
        settings.active_academic_year = year
    if results_published is not None:
        settings.results_published = bool(results_published)
    db.session.commit()
    return settings, None


def update_group_size_range(min_size, max_size):
    return update_settings(min_size, max_size)
