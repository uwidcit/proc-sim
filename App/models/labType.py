from App.database import db

class LabType(db.Model):
    __tablename__ = 'lab_type'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)
    description = db.Column(db.String(1000), nullable=False)

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def get_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }
