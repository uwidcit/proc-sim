from App.database import db
from datetime import datetime


class RFP(db.Model):
    groupID = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    lotID = db.Column(db.Integer, db.ForeignKey('lot.id'), primary_key=True)
    # draft = editable, not in gallery; submitted = published & immutable
    status = db.Column(db.String(30), default="draft")
    timestamp = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    deviceType = db.Column(db.String(1000), default="")
    resolution = db.Column(db.String(1000), default="")
    os = db.Column(db.String(1000), default="")
    cpu = db.Column(db.String(1000), default="")
    ram = db.Column(db.String(1000), default="")
    drive = db.Column(db.String(1000), default="")
    gpu = db.Column(db.String(1000), default="")
    peripherals = db.Column(db.String(1000), default="")
    features = db.Column(db.String(1000), default="")
    io = db.Column(db.String(1000), default="")

    def __init__(self, groupID, lotID):
        self.groupID = groupID
        self.lotID = lotID
        self.status = "draft"
        self.timestamp = datetime.now()

    def get_json(self):
        from App.controllers.rfp import RFP_SPEC_CATEGORIES

        payload = {
            "groupID": self.groupID,
            "lotID": self.lotID,
            "status": self.status,
        }
        for key, label in RFP_SPEC_CATEGORIES:
            payload[label] = getattr(self, key, "") or ""
        return payload
