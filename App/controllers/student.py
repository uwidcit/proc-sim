from App.models import Student
from App.database import db


def create_student(name, username, password, email=None):
    newstudent = Student(name=name, username=username, password=password, email=email)
    db.session.add(newstudent)
    db.session.commit()
    return newstudent


def get_student(id):
    return db.session.get(Student, id)


def get_student_by_username(username):
    return db.session.scalars(
        db.select(Student).filter_by(username=username)
    ).first()


def get_all_students():
    return db.session.scalars(db.select(Student)).all()


def get_all_students_json():
    students = get_all_students()
    if not students:
        return []
    return [student.get_json() for student in students]
