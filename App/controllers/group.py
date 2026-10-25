import re

from App.models import *
from .studentGroup import remove_studentGroup, add_studentGroup
from .lotGroup import remove_lotGroup
from .academic_year import get_current_year
from App.database import db


# Display names are capped so "G{n} {name}" fits in group.groupName (80).
MAX_DISPLAY_NAME_LEN = 40
_GROUP_PREFIX_RE = re.compile(r"^G(\d+)\s+(.*)$", re.IGNORECASE)


def parse_group_label(group_name):
    """Return (number, display_name). number is None when no G# prefix."""
    name = group_name or ""
    match = _GROUP_PREFIX_RE.match(name)
    if match:
        return int(match.group(1)), match.group(2)
    return None, name


def format_group_name(number, display_name):
    return f"G{int(number)} {(display_name or '').strip()}"


def next_group_number(academic_year=None):
    """Next incremental group label for the academic year (starts at 1)."""
    if academic_year is None:
        academic_year = get_current_year()
    max_n = 0
    for group in get_all_groups(academic_year=academic_year):
        number, _ = parse_group_label(group.groupName)
        if number is not None and number > max_n:
            max_n = number
    return max_n + 1


def renumber_groups_for_year(academic_year=None):
    """
    Reset G# labels for a year to G1..Gn (creation order by id).
    Other years are untouched. Returns the renumbered groups.
    """
    if academic_year is None:
        academic_year = get_current_year()

    groups = db.session.scalars(
        db.select(Group)
        .filter_by(academic_year=academic_year)
        .order_by(Group.id)
    ).all()
    if not groups:
        return []

    # Two-pass to avoid unique (groupName, academic_year) collisions
    pending = []
    for group in groups:
        _, display = parse_group_label(group.groupName)
        display = (display or "").strip() or "Untitled"
        pending.append((group, display))
        group.groupName = f"__tmp_{group.id}__"
    db.session.flush()

    for index, (group, display) in enumerate(pending, start=1):
        group.groupName = format_group_name(index, display)
    db.session.commit()
    return groups


def create_group(groupName, academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    display = (groupName or "").strip()[:MAX_DISPLAY_NAME_LEN] or "Untitled"
    number = next_group_number(academic_year)
    group = Group(format_group_name(number, display), academic_year=academic_year)
    db.session.add(group)
    db.session.commit()
    return group


def display_group_name(group):
    """User-facing name without the G{n} prefix."""
    if not group:
        return ""
    _, display = parse_group_label(group.groupName)
    return display


def _validate_display_name(group_name):
    group_name = (group_name or "").strip()
    if not group_name:
        return None, "You must enter a group name"
    if len(group_name) > MAX_DISPLAY_NAME_LEN:
        return None, f"Group name must be {MAX_DISPLAY_NAME_LEN} characters or fewer"
    return group_name, None


def update_pending_group(group_id, group_name, member_ids):
    """
    Update name and members of a pending (requested) group.
    Returns (group, None) or (None, error_message).
    """
    group = get_group(group_id)
    if not group:
        return None, "Group not found"
    if group.status != "requested":
        return None, "Only pending group requests can be edited"

    group_name, err = _validate_display_name(group_name)
    if err:
        return None, err

    member_ids = [int(m) for m in member_ids]
    if not member_ids:
        return None, "Group must have members"

    # Ensure no other pending/approved group in this year holds these students
    year = group.academic_year
    for sid in member_ids:
        existing = db.session.scalars(
            db.select(StudentGroup)
            .join(Group, Group.id == StudentGroup.groupID)
            .filter(
                StudentGroup.studentID == sid,
                Group.academic_year == year,
                Group.id != group.id,
            )
        ).first()
        if existing:
            return None, "One or more selected students are already in another group"

    current = db.session.scalars(
        db.select(StudentGroup).filter_by(groupID=group.id)
    ).all()
    current_ids = {m.studentID for m in current}
    desired = set(member_ids)

    for sid in current_ids - desired:
        remove_studentGroup(sid, group.id)
    for sid in desired - current_ids:
        add_studentGroup(sid, group.id)

    number, _ = parse_group_label(group.groupName)
    if number is None:
        number = next_group_number(year)
    group.groupName = format_group_name(number, group_name)
    db.session.commit()
    return group, None


def approve_group(id):
    group = get_group(id)
    group.status = "approved"
    db.session.commit()


def rename_group(group_id, group_name):
    """
    Set the display name for a group (keeps existing G{n} label).
    Returns (group, None) or (None, error_message).
    """
    group = get_group(group_id)
    if not group:
        return None, "Group not found"
    group_name, err = _validate_display_name(group_name)
    if err:
        return None, err

    number, _ = parse_group_label(group.groupName)
    if number is None:
        number = next_group_number(group.academic_year)
    group.groupName = format_group_name(number, group_name)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return None, "Could not update group name (it may already be in use)"
    return group, None


def set_group_members(group_id, member_ids):
    """
    Replace membership for a group (admin). Member IDs must belong to the
    group's academic year. Returns (group, None) or (None, error_message).
    """
    group = get_group(group_id)
    if not group:
        return None, "Group not found"

    try:
        member_ids = [int(m) for m in (member_ids or []) if str(m).strip()]
    except (TypeError, ValueError):
        return None, "Invalid member list"

    year = group.academic_year
    desired = set()
    for sid in member_ids:
        student = db.session.get(Student, sid)
        if not student or student.academic_year != year:
            return None, f"Student {sid} is not in the {year} class list"
        desired.add(sid)

    current = db.session.scalars(
        db.select(StudentGroup).filter_by(groupID=group.id)
    ).all()
    current_ids = {m.studentID for m in current}

    for sid in current_ids - desired:
        remove_studentGroup(sid, group.id)

    for sid in desired - current_ids:
        # Pull out of any other group in this year before joining
        others = db.session.scalars(
            db.select(StudentGroup)
            .join(Group, Group.id == StudentGroup.groupID)
            .filter(
                StudentGroup.studentID == sid,
                Group.academic_year == year,
                Group.id != group.id,
            )
        ).all()
        for m in others:
            remove_studentGroup(m.studentID, m.groupID)
        add_studentGroup(sid, group.id)

    return get_group(group_id), None


def admin_create_group(group_name, member_ids=None, approve=False, academic_year=None):
    """
    Create a group for the year, optionally with members and auto-approve.
    Returns (group, None) or (None, error_message).
    """
    group_name, err = _validate_display_name(group_name)
    if err:
        return None, err
    if academic_year is None:
        academic_year = get_current_year()

    group = create_group(group_name, academic_year=academic_year)
    if member_ids:
        updated, err = set_group_members(group.id, member_ids)
        if err:
            remove_group(group.id)
            return None, err
        group = updated

    if approve:
        from .lotGroup import assign_exclusive_lots
        ok, err = assign_exclusive_lots(group.id, count=2)
        if not ok:
            # Keep the group even if lots cannot be assigned; mark approved without lots
            approve_group(group.id)
            return get_group(group.id), (
                f"Group created, but lots could not be assigned: {err}"
            )

    return get_group(group.id), None


def get_group(id):
    return db.session.get(Group, id)

def get_all_groups(academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(Group).filter_by(academic_year=academic_year)
    ).all()

def get_all_groups_json(academic_year=None):
    groups = get_all_groups(academic_year=academic_year)
    if not groups:
        return []
    groups = [group.get_json() for group in groups]
    return groups

def remove_group(id):
    group = get_group(id)
    if group:
        members = db.session.scalars(
            db.select(StudentGroup)
            .filter_by(groupID=id)
        ).all()

        for member in members:
            remove_studentGroup(member.studentID, member.groupID)

        lotGroups = db.session.scalars(
            db.select(LotGroup)
            .filter_by(groupID=id)
        ).all()

        for lotGroup in lotGroups:
            remove_lotGroup(lotGroup.lotID, lotGroup.groupID)
        
        db.session.delete(group)
        db.session.commit()
        return True
    return False
