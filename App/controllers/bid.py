from App.models import Bid, Evaluation, Lot
from App.database import db
from .academic_year import get_current_year

def create_bid(lotID, sourceGroupID, recipientGroupID, bidDocument, bidDocumentName, quotationAmount):
    newbid = Bid(lotID, sourceGroupID, recipientGroupID, bidDocument, bidDocumentName, quotationAmount)
    db.session.add(newbid)
    db.session.commit()
    return newbid

def get_bid(id):
    return db.session.get(Bid, id)

def get_all_bids(academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(Bid)
        .join(Lot, Lot.id == Bid.lotID)
        .filter(Lot.academic_year == academic_year)
    ).all()

def get_all_bids_json(academic_year=None):
    bids = get_all_bids(academic_year=academic_year)
    if not bids:
        return []
    bids = [bid.get_json() for bid in bids]
    return bids

def remove_bid(id):
    bid = get_bid(id)
    if bid:
        evaluations = db.session.scalars(
            db.select(Evaluation)
            .filter_by(bidID=bid.id)
        )

        for evaluation in evaluations:
            db.session.delete(evaluation)
        
        db.session.delete(bid)
        db.session.commit()
        return True
    return False