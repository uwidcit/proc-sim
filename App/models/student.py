from App.database import db
from .user import User

class Student(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True, unique=True)

    __mapper_args__ = {
        'polymorphic_identity': 'student'
    }

    def __init__(self, name, username, password, email=None):
        super().__init__(username, password)
        self.name = name
        self.email = email

    def is_admin(self):
        return False
    
    def is_student(self):
        return True

    def get_json(self):
        return {**super().get_json(), 'role': 'student'}