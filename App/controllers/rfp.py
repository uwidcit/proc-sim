from App.models import RFP, Bid, Lot
from App.database import db
from .lot import get_lot
from .bid import remove_bid
from .academic_year import get_current_year


RFP_FIELDS = (
    "deviceType", "resolution", "os", "cpu", "ram", "drive",
    "gpu", "peripherals", "features", "io",
)

# Canonical RFP / technical-audit categories (key, label) — keep in sync with Create RFP form
RFP_SPEC_CATEGORIES = (
    ("deviceType", "Device type"),
    ("resolution", "Screen size & resolution"),
    ("os", "Operating system(s)"),
    ("cpu", "CPU"),
    ("ram", "Memory (RAM)"),
    ("drive", "Hard drive / storage"),
    ("gpu", "Graphics"),
    ("peripherals", "External peripherals"),
    ("features", "Features"),
    ("io", "I/O"),
)

RFP_SPEC_LABELS = dict(RFP_SPEC_CATEGORIES)


def rfp_specs_dict(rfp):
    """Map an RFP (or similar) to {field: value} for all audit categories."""
    if not rfp:
        return {key: "" for key, _ in RFP_SPEC_CATEGORIES}
    return {
        key: (getattr(rfp, key, None) or "")
        for key, _ in RFP_SPEC_CATEGORIES
    }


def _apply_specs(rfp, specs):
    for field in RFP_FIELDS:
        if field in specs and specs[field] is not None:
            setattr(rfp, field, specs[field])


def create_rfp(groupID, lotID, status="draft", **specs):
    existing = get_rfp(groupID, lotID)
    if existing:
        return existing

    rfp = RFP(groupID, lotID)
    # Start blank; only apply explicitly provided specs (do not copy lot catalog)
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
