"""Admin testing persona: a claimed student in a pre-approved group."""

from __future__ import annotations

from App.database import db
from App.models import Group, Student, StudentGroup
from App.controllers.academic_year import get_active_year
from App.controllers.student import create_student
from App.controllers.group import admin_create_group, approve_group, create_group
from App.controllers.studentGroup import add_studentGroup, check_studentGroup
from App.controllers.lotGroup import assign_exclusive_lots

ADMIN_SANDBOX_NAME = "Admin Tester"
ADMIN_SANDBOX_GROUP = "AdminLab"
ADMIN_SANDBOX_PASSWORD = "plattech2026"
ADMIN_SANDBOX_SEQ = 9999


def admin_sandbox_username(year=None):
    if year is None:
        year = get_active_year()
    return f"{int(year)}{ADMIN_SANDBOX_SEQ:04d}"


def get_admin_sandbox_student(year=None):
    if year is None:
        year = get_active_year()
    username = admin_sandbox_username(year)
    return db.session.scalars(
        db.select(Student).filter_by(username=username)
    ).first()


def ensure_admin_sandbox(year=None, password=ADMIN_SANDBOX_PASSWORD):
    """
    Ensure a claimed student + approved AdminLab group (with lots when possible)
    exist for the academic year. Returns (student, group).
    """
    if year is None:
        year = get_active_year()
    year = int(year)

    student = get_admin_sandbox_student(year)
    if not student:
        student = create_student(
            ADMIN_SANDBOX_NAME,
            admin_sandbox_username(year),
            password,
            email=f"adminlab{year}@lab.local",
            academic_year=year,
            account_claimed=True,
        )
    else:
        student.account_claimed = True
        if student.academic_year != year:
            student.academic_year = year
        db.session.commit()

    membership = check_studentGroup(student.id, academic_year=year)
    group = None
    if membership:
        group = db.session.get(Group, membership.groupID)

    if not group:
        # Prefer an existing AdminLab label for the year
        for candidate in db.session.scalars(
            db.select(Group).filter_by(academic_year=year)
        ).all():
            if ADMIN_SANDBOX_GROUP in (candidate.groupName or ""):
                group = candidate
                break

    if not group:
        group, err = admin_create_group(
            ADMIN_SANDBOX_GROUP,
            member_ids=[student.id],
            approve=True,
            academic_year=year,
        )
        if err and not group:
            # Fallback: create + approve without lots
            group = create_group(ADMIN_SANDBOX_GROUP, academic_year=year)
            add_studentGroup(student.id, group.id)
            ok, _ = assign_exclusive_lots(group.id, count=2)
            if not ok:
                approve_group(group.id)
        return student, group

    # Ensure membership + approved + lots
    already = db.session.scalars(
        db.select(StudentGroup).filter_by(studentID=student.id, groupID=group.id)
    ).first()
    if not already:
        add_studentGroup(student.id, group.id)

    if group.status != "approved":
        ok, _ = assign_exclusive_lots(group.id, count=2)
        if not ok:
            approve_group(group.id)

    return student, group
