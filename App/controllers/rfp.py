from App.models import RFP, Bid, Lot
from App.database import db
from .lot import get_lot
from .bid import remove_bid
from .academic_year import get_current_year


RFP_FIELDS = (
    "deviceType", "resolution", "os", "cpu", "ram", "drive",
    "gpu", "peripherals", "features", "io",
)


def _apply_specs(rfp, specs):
    for field in RFP_FIELDS:
        if field in specs and specs[field] is not None:
            setattr(rfp, field, specs[field])


def create_rfp(groupID, lotID, status="draft", **specs):
    existing = get_rfp(groupID, lotID)
    if existing:
        return existing

    rfp = RFP(groupID, lotID)
    lot = get_lot(lotID)
    if lot:
        for field in RFP_FIELDS:
            setattr(rfp, field, getattr(lot, field, "") or "")
    _apply_specs(rfp, specs)
    rfp.status = status
    db.session.add(rfp)
    db.session.commit()
    return rfp


def save_rfp_draft(groupID, lotID, **specs):
    rfp = get_rfp(groupID, lotID)
    if rfp and rfp.status == "submitted":
        return None, "RFP has already been submitted and cannot be changed"
    if not rfp:
        rfp = create_rfp(groupID, lotID, status="draft", **specs)
        return rfp, None
    _apply_specs(rfp, specs)
    rfp.status = "draft"
    db.session.commit()
    return rfp, None


def submit_rfp(groupID, lotID, **specs):
    rfp = get_rfp(groupID, lotID)
    if rfp and rfp.status == "submitted":
        return None, "RFP has already been submitted and cannot be changed"
    if not rfp:
        rfp = create_rfp(groupID, lotID, status="submitted", **specs)
        return rfp, None
    _apply_specs(rfp, specs)
    rfp.status = "submitted"
    db.session.commit()
    return rfp, None


def approve_rfp(groupID, lotID):
    """Legacy alias: publish RFP immediately (submit)."""
    rfp = get_rfp(groupID, lotID)
    if rfp:
        rfp.status = "submitted"
        db.session.commit()
    return rfp


def get_rfp(groupID, lotID):
    return db.session.get(RFP, (int(groupID), int(lotID)))


def get_all_rfps(academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(RFP)
        .join(Lot, Lot.id == RFP.lotID)
        .filter(Lot.academic_year == academic_year)
    ).all()


def get_submitted_rfps(academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(RFP)
        .join(Lot, Lot.id == RFP.lotID)
        .filter(Lot.academic_year == academic_year, RFP.status == "submitted")
    ).all()


def get_all_rfps_json(academic_year=None):
    rfps = get_all_rfps(academic_year=academic_year)
    if not rfps:
        return []
    return [rfp.get_json() for rfp in rfps]


def remove_rfp(groupID, lotID):
    rfp = get_rfp(groupID, lotID)
    if rfp:
        bids = db.session.scalars(
            db.select(Bid).filter_by(lotID=lotID)
        ).all()
        for bid in bids:
            remove_bid(bid.id)
        db.session.delete(rfp)
        db.session.commit()
        return True
    return False
