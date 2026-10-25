from App.models import StudentGroup, Group
from App.database import db
from .academic_year import get_current_year


def add_studentGroup(studentID, groupID):
    newentry = StudentGroup(studentID, groupID)
    db.session.add(newentry)
    db.session.commit()

def get_studentGroup(studentID, groupID):
    return db.session.get(StudentGroup, (studentID, groupID))

def check_studentGroup(studentID, academic_year=None):
    """Return membership for this student in the given academic year (current by default)."""
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(StudentGroup)
        .join(Group, Group.id == StudentGroup.groupID)
        .filter(
            StudentGroup.studentID == studentID,
            Group.academic_year == academic_year,
        )
    ).first()

def students_in_groups_for_year(academic_year=None):
    """Student IDs already assigned to a group in the given year."""
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(StudentGroup.studentID)
        .join(Group, Group.id == StudentGroup.groupID)
        .filter(Group.academic_year == academic_year)
    ).all()

def get_all_studentGroups():
    return db.session.scalars(
        db.select(StudentGroup)
    ).all()

def get_all_studentGroups_json():
    entries = get_all_studentGroups()
    if not entries:
        return []
    entries = [entry.get_json() for entry in entries]
    return entries

def remove_studentGroup(studentID, groupID):
    entry = get_studentGroup(studentID, groupID)
    if entry:
        db.session.delete(entry)
        db.session.commit()
        return True
    return False


def move_student_to_group(student_id, group_id=None, academic_year=None):
    """
    Move a student into a group for the year, or ungroup if group_id is None.
    Removes any other membership in that year first.
    Returns (True, None) or (False, error_message).
    """
    from App.models import Student

    if academic_year is None:
        academic_year = get_current_year()

    student = db.session.get(Student, student_id)
    if not student:
        return False, "Student not found"
    if student.academic_year != academic_year:
        return False, f"Student is not on the {academic_year} class list"

    if group_id is not None:
        group = db.session.get(Group, group_id)
        if not group:
            return False, "Group not found"
        if group.academic_year != academic_year:
            return False, "Group is not for this academic year"

    # Drop current-year memberships
    memberships = db.session.scalars(
        db.select(StudentGroup)
        .join(Group, Group.id == StudentGroup.groupID)
        .filter(
            StudentGroup.studentID == student_id,
            Group.academic_year == academic_year,
        )
    ).all()
    for m in memberships:
        db.session.delete(m)
    db.session.flush()

    if group_id is not None:
        db.session.add(StudentGroup(student_id, group_id))

    db.session.commit()
    return True, None
