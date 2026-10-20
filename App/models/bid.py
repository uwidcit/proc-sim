from App.database import db
from datetime import datetime

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lotID = db.Column(db.Integer, db.ForeignKey('lot.id'), nullable=False)
    sourceGroupID = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    recipientGroupID = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    bidDocument = db.Column(db.LargeBinary, nullable=False)
    bidDocumentName = db.Column(db.String(255), nullable=False)
    quotationAmount = db.Column(db.Float, default=0.0)

    def __init__(self, lotID, sourceGroupID, recipientGroupID, bidDocument, bidDocumentName, quotationAmount):
        self.lotID = lotID
        self.sourceGroupID = sourceGroupID
        self.recipientGroupID = recipientGroupID
        self.bidDocument = bidDocument
        self.bidDocumentName = bidDocumentName
        self.quotationAmount = quotationAmount
        self.timestamp = datetime.now()

    def get_json(self):
        return {
            'id': self.id,
            'lotID': self.lotID,
            'sourceGroupID': self.sourceGroupID,
            'recipientGroupID': self.recipientGroupID,
            'timestamp': self.timestamp.isoformat(),
            'bidDocumentName': self.bidDocumentName
        }