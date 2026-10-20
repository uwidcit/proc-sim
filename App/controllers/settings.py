from App.models import AppSetting
from App.database import db


def get_or_create_settings():
    settings = db.session.scalars(db.select(AppSetting)).first()
    if not settings:
        settings = AppSetting(group_size_min=3, group_size_max=3)
        db.session.add(settings)
        db.session.commit()
    return settings


def get_group_size_range():
    settings = get_or_create_settings()
    return settings.group_size_min, settings.group_size_max


def update_group_size_range(min_size, max_size):
    min_size = int(min_size)
    max_size = int(max_size)
    if min_size < 1 or max_size < min_size:
        return None, "Invalid group size range"
    settings = get_or_create_settings()
    settings.group_size_min = min_size
    settings.group_size_max = max_size
    db.session.commit()
    return settings, None
