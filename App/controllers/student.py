from App.models import Student, User
from App.database import db
from .academic_year import get_current_year, get_active_year


def create_student(name, username, password, email=None, academic_year=None):
    if academic_year is None:
        academic_year = get_active_year()
    newstudent = Student(
        name=name,
        username=username,
        password=password,
        email=email,
        academic_year=academic_year,
    )
    db.session.add(newstudent)
    db.session.commit()
    return newstudent


def register_student(name, student_id, password, confirm_password, email=None):
    """
    Public self-serve student signup for the active working year.
    Returns (student, None) on success or (None, error_message) on failure.
    """
    name = (name or "").strip()
    student_id = (student_id or "").strip()
    email = (email or "").strip().lower() or None
    password = password or ""
    confirm_password = confirm_password or ""
    year = get_active_year()

    if not name:
        return None, "Full name is required"
    if len(name) > 100:
        return None, "Name is too long"
    if not student_id:
        return None, "Student ID is required"
    if len(student_id) > 20:
        return None, "Student ID must be 20 characters or fewer"
    if " " in student_id:
        return None, "Student ID cannot contain spaces"
    if email and ("@" not in email or len(email) > 120):
        return None, "Enter a valid email address"
    if len(password) < 6:
        return None, "Password must be at least 6 characters"
    if password != confirm_password:
        return None, "Passwords do not match"

    if db.session.scalars(db.select(User).filter_by(username=student_id)).first():
        return None, "That student ID is already registered"
    if email and db.session.scalars(
        db.select(Student).filter_by(email=email, academic_year=year)
    ).first():
        return None, "That email is already registered for this year"

    student = create_student(
        name, student_id, password, email=email, academic_year=year
    )
    return student, None


def get_student(id):
    return db.session.get(Student, id)


def get_student_by_username(username):
    return db.session.scalars(
        db.select(Student).filter_by(username=username)
    ).first()


def get_all_students(academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(Student)
        .filter_by(academic_year=academic_year)
        .order_by(Student.name)
    ).all()


def get_all_students_json(academic_year=None):
    students = get_all_students(academic_year=academic_year)
    if not students:
        return []
    return [student.get_json() for student in students]
