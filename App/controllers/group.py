from App.models import *
from .bid import remove_bid
from .evaluation import remove_evaluation
from .rfp import remove_rfp
from .studentGroup import remove_studentGroup, add_studentGroup
from .lotGroup import remove_lotGroup
from .academic_year import get_current_year
from App.database import db
from sqlalchemy import or_


def create_group(groupName, academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    group = Group(groupName, academic_year=academic_year)
    db.session.add(group)
    db.session.flush()
    group.set_generated_name()
    db.session.commit()
    return group


def display_group_name(group):
    """User-facing name without the G{id} prefix."""
    if not group:
        return ""
    prefix = f"G{group.id} "
    name = group.groupName or ""
    if name.startswith(prefix):
        return name[len(prefix):]
    return name


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

    group_name = (group_name or "").strip()
    if not group_name:
        return None, "You must enter a group name"
    if len(group_name) > 30:
        return None, "Group name is too long"

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

    group.groupName = f"G{group.id} {group_name}"
    db.session.commit()
    return group, None


def approve_group(id):
    group = get_group(id)
    group.status = "approved"
    db.session.commit()

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
