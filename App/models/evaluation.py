from App.database import db
from datetime import datetime

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sourceGroupID = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    recipientGroupID = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    bidID = db.Column(db.Integer, db.ForeignKey('bid.id'), nullable=False)
    lotID = db.Column(db.Integer, db.ForeignKey('lot.id'), nullable=False)
    specsSelected = db.Column(db.String(500), default="")
    status = db.Column(db.String(30), default="draft")
    overallScore = db.Column(db.Float, default=0.0)
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
    professionalism = db.Column(db.Integer, default=0)
    presentation = db.Column(db.Integer, default=0)
    budget = db.Column(db.Integer, default=0)
    specsMet = db.Column(db.Integer, default=0)

    def __init__(self, sourceGroupID, recipientGroupID, bidID, lotID, specsMet, presentation, professionalism, budget):
        self.bidID = bidID
        self.lotID = lotID
        self.sourceGroupID = sourceGroupID
        self.recipientGroupID = recipientGroupID
        self.specsMet = specsMet
        self.presentation = presentation
        self.professionalism = professionalism
        self.budget = budget
        self.overallScore = round((((specsMet + presentation + professionalism + budget)/25) * 10), 1)
        self.timestamp = datetime.now()
        
    def get_json(self):
        return {
            'id': self.id,
            'sourceGroupID': self.sourceGroupID,
            'recipientGroupID': self.recipientGroupID,
            'bidID': self.bidID,
            'lotID': self.lotID,
            'overallScore': self.overallScore
        }