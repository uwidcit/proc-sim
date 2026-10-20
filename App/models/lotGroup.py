from App.database import db


class LotGroup(db.Model):
    # Exclusive: each lot belongs to at most one group
    lotID = db.Column(db.Integer, db.ForeignKey('lot.id'), primary_key=True)
    groupID = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False, index=True)

    def __init__(self, lotID, groupID):
        self.lotID = lotID
        self.groupID = groupID

    def get_json(self):
        return {
            'lotID': self.lotID,
            'groupID': self.groupID
        }
