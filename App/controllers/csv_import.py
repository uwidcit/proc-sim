import csv
import io
import secrets
import string
from collections import defaultdict

from App.database import db
from App.models import Student, StudentGroup, Group, LotGroup, Lot
from .settings import get_group_size_range
from .academic_year import get_current_year


REQUIRED_HEADERS = {"student_id", "name", "email", "group_name"}


def _generate_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def parse_groups_csv(file_storage):
    """Parse and validate CSV. Returns (groups_dict, errors)."""
    raw = file_storage.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        return None, ["CSV has no header row"]

    headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing = REQUIRED_HEADERS - headers
    if missing:
        return None, [f"Missing required columns: {', '.join(sorted(missing))}"]

    field_map = {h.strip().lower(): h for h in reader.fieldnames if h}

    groups = defaultdict(list)
    seen_ids = set()
    seen_emails = set()
    errors = []

    for i, row in enumerate(reader, start=2):
        student_id = (row.get(field_map["student_id"]) or "").strip()
        name = (row.get(field_map["name"]) or "").strip()
        email = (row.get(field_map["email"]) or "").strip().lower()
        group_name = (row.get(field_map["group_name"]) or "").strip()

        if not all([student_id, name, email, group_name]):
            errors.append(f"Row {i}: all fields are required")
            continue
        if student_id in seen_ids:
            errors.append(f"Row {i}: duplicate student_id {student_id}")
            continue
        if email in seen_emails:
            errors.append(f"Row {i}: duplicate email {email}")
            continue
        seen_ids.add(student_id)
        seen_emails.add(email)
        groups[group_name].append({
            "student_id": student_id,
            "name": name,
            "email": email,
            "group_name": group_name,
        })

    if errors:
        return None, errors

    min_size, max_size = get_group_size_range()
    for gname, members in groups.items():
        n = len(members)
        if n < min_size or n > max_size:
            errors.append(
                f"Group '{gname}' has {n} members; allowed range is {min_size}-{max_size}"
            )

    if errors:
        return None, errors

    from .lotGroup import count_unassigned_lots
    free_count = count_unassigned_lots()
    needed = 2 * len(groups)
    if free_count < needed:
        return None, [
            f"Not enough unassigned lots for auto-approve. Need {needed}, found {free_count}."
        ]

    year = get_current_year()
    # Conflict checks against existing users (email unique within year)
    for gname, members in groups.items():
        for m in members:
            if db.session.scalars(db.select(Student).filter_by(username=m["student_id"])).first():
                errors.append(f"Student ID {m['student_id']} already exists")
            if db.session.scalars(
                db.select(Student).filter_by(email=m["email"], academic_year=year)
            ).first():
                errors.append(f"Email {m['email']} already exists for {year}")

    if errors:
        return None, errors

    return dict(groups), []


def import_groups_from_csv(file_storage):
    """
    Import groups in a single transaction. Returns (credentials, errors).
    """
    groups, errors = parse_groups_csv(file_storage)
    if errors:
        return None, errors

    credentials = []
    try:
        from .lotGroup import get_unassigned_lots
        lot_iter = iter(get_unassigned_lots())

        year = get_current_year()
        for group_name, members in groups.items():
            group = Group(group_name, academic_year=year)
            db.session.add(group)
            db.session.flush()
            group.set_generated_name()

            for m in members:
                password = _generate_password()
                student = Student(
                    m["name"],
                    m["student_id"],
                    password,
                    email=m["email"],
                    academic_year=year,
                )
                db.session.add(student)
                db.session.flush()
                db.session.add(StudentGroup(student.id, group.id))
                credentials.append({
                    "student_id": m["student_id"],
                    "email": m["email"],
                    "temporary_password": password,
                    "group_name": group_name,
                })

            for _ in range(2):
                lot = next(lot_iter, None)
                if lot is None:
                    raise ValueError("Not enough unassigned lots during import")
                db.session.add(LotGroup(lot.id, group.id))

            group.status = "approved"

        db.session.commit()
        return credentials, []
    except Exception as e:
        db.session.rollback()
        return None, [str(e)]


def credentials_to_csv(credentials):
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["student_id", "email", "temporary_password", "group_name"],
    )
    writer.writeheader()
    for row in credentials:
        writer.writerow(row)
    return buf.getvalue()
