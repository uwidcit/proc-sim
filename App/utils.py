"""Shared helpers for the procurement simulator."""
from datetime import datetime

CURRENCY_CODE = "TTD"


def format_timestamp(value):
    """Portable datetime display (avoids Windows-only %# format codes)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime("%m/%d/%Y, %I:%M%p").lstrip("0").replace(" 0", " ").lower()


def format_money(value, decimals=2):
    """Format an amount as Trinidad and Tobago Dollars (TTD)."""
    if value is None or value == "":
        return f"{CURRENCY_CODE} 0.00"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return f"{CURRENCY_CODE} 0.00"
    return f"{CURRENCY_CODE} {amount:,.{decimals}f}"


def get_current_student_group(student_id, academic_year=None):
    from App.database import db
    from App.models import Group, StudentGroup
    from App.controllers.academic_year import get_current_year

    if academic_year is None:
        academic_year = get_current_year()

    return db.session.scalars(
        db.select(Group)
        .join(StudentGroup, StudentGroup.groupID == Group.id)
        .filter(
            StudentGroup.studentID == student_id,
            Group.academic_year == academic_year,
        )
    ).first()


def get_lot_owner_group_id(lot_id):
    from App.database import db
    from App.models import LotGroup

    entry = db.session.scalars(
        db.select(LotGroup).filter_by(lotID=int(lot_id))
    ).first()
    return entry.groupID if entry else None


def validate_pdf_upload(file_storage, max_bytes=5 * 1024 * 1024):
    """Return (ok, error_message)."""
    if not file_storage or not file_storage.filename:
        return False, "PDF file is required"
    name = file_storage.filename.lower()
    if not name.endswith(".pdf"):
        return False, "Only PDF uploads are allowed"
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_bytes:
        return False, "PDF must be 5MB or smaller"
    header = file_storage.stream.read(5)
    file_storage.stream.seek(0)
    if header != b"%PDF-":
        return False, "Invalid PDF file"
    return True, None
