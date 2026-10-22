from App.database import db
from App.academic_years import DEFAULT_ACADEMIC_YEAR
from .user import User


class Student(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    academic_year = db.Column(
        db.Integer, nullable=False, default=DEFAULT_ACADEMIC_YEAR, index=True
    )
    # False = roster placeholder; student claims via register (id + email match)
    account_claimed = db.Column(db.Boolean, nullable=False, default=True)

    __mapper_args__ = {
        'polymorphic_identity': 'student'
    }

    def __init__(
        self,
        name,
        username,
        password,
        email=None,
        academic_year=None,
        account_claimed=True,
    ):
        super().__init__(username, password)
        self.name = name
        self.email = email
        self.academic_year = (
            academic_year if academic_year is not None else DEFAULT_ACADEMIC_YEAR
        )
        self.account_claimed = account_claimed

    def is_admin(self):
        return False

    def is_student(self):
        return True

    def get_json(self):
        return {
            **super().get_json(),
            'role': 'student',
            'academic_year': self.academic_year,
            'account_claimed': self.account_claimed,
        }
