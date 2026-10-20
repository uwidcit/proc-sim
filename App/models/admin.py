from App.database import db
from .user import User

class Admin(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'admin'
    }

    def __init__(self, username, password):
        super().__init__(username, password)

    def is_admin(self):
        return True
    
    def is_student(self):
        return False

    def get_json(self):
        return {**super().get_json(), 'role': 'admin'}