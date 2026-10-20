from App.database import db

class StudentGroup(db.Model):
    studentID = db.Column(db.Integer, db.ForeignKey('student.id'), primary_key=True)
    groupID = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)

    def __init__(self, studentID, groupID):
        self.studentID = studentID
        self.groupID = groupID

    def get_json(self):
        return {
            'studentID': self.studentID,
            'groupID': self.groupID
        }