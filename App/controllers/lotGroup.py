from App.models import LotGroup, RFP, Bid, Evaluation, Group, Lot
from App.database import db
from sqlalchemy import and_, or_
from .rfp import remove_rfp
from .bid import remove_bid
from .evaluation import remove_evaluation
from .academic_year import get_current_year


def add_lotGroup(lotID, groupID):
    existing = db.session.scalars(
        db.select(LotGroup).filter_by(lotID=int(lotID))
    ).first()
    if existing:
        return None
    newentry = LotGroup(int(lotID), int(groupID))
    db.session.add(newentry)
    db.session.commit()
    return newentry


def get_lotGroup(lotID, groupID):
    return db.session.get(LotGroup, int(lotID))


def get_all_lotGroups(academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(LotGroup)
        .join(Lot, Lot.id == LotGroup.lotID)
        .filter(Lot.academic_year == academic_year)
    ).all()


def get_all_lotGroups_json(academic_year=None):
    entries = get_all_lotGroups(academic_year=academic_year)
    if not entries:
        return []
    return [entry.get_json() for entry in entries]


def get_unassigned_lots(limit=None, academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    assigned_ids = db.session.scalars(
        db.select(LotGroup.lotID)
        .join(Lot, Lot.id == LotGroup.lotID)
        .filter(Lot.academic_year == academic_year)
    ).all()
    query = db.select(Lot).filter_by(academic_year=academic_year).order_by(Lot.id)
    if assigned_ids:
        query = query.where(Lot.id.notin_(assigned_ids))
    lots = db.session.scalars(query).all()
    if limit is not None:
        return lots[:limit]
    return lots


def count_unassigned_lots(academic_year=None):
    return len(get_unassigned_lots(academic_year=academic_year))


def assign_exclusive_lots(group_id, count=2):
    """
    Assign the next `count` unassigned lots (lowest IDs) to the group and approve it.
    Returns (True, None) on success or (False, error_message) on failure.
    Does not change group status on failure.
    """
    from .group import approve_group, get_group

    group = get_group(group_id)
    if not group:
        return False, "Group not found"

    already = db.session.scalars(
        db.select(LotGroup).filter_by(groupID=group_id)
    ).first()
    if already:
        return False, "Lots have already been assigned for this group"

    free = get_unassigned_lots(limit=count, academic_year=group.academic_year)
    if len(free) < count:
        return False, f"Not enough unassigned lots. Need {count}, found {len(free)}."

    for lot in free:
        db.session.add(LotGroup(lot.id, group_id))
    db.session.flush()
    approve_group(group_id)
    return True, None


def remove_lotGroup(lotID, groupID):
    entry = get_lotGroup(lotID, groupID)
    if entry and entry.groupID == int(groupID):
        group = db.session.scalars(
            db.select(Group).filter_by(id=groupID)
        ).first()

        if group:
            remaining = db.session.scalars(
                db.select(LotGroup).filter(
                    and_(LotGroup.groupID == groupID, LotGroup.lotID != int(lotID))
                )
            ).first()
            if not remaining:
                group.status = "requested"

        rfps = db.session.scalars(
            db.select(RFP).filter(or_(RFP.lotID == lotID, RFP.groupID == groupID))
        ).all()

        for rfp in rfps:
            remove_rfp(rfp.groupID, rfp.lotID)

        bids = db.session.scalars(
            db.select(Bid).filter(
                or_(Bid.lotID == lotID, Bid.sourceGroupID == groupID, Bid.recipientGroupID == groupID)
            )
        ).all()

        for bid in bids:
            remove_bid(bid.id)

        evals = db.session.scalars(
            db.select(Evaluation).filter(
                or_(
                    Evaluation.sourceGroupID == groupID,
                    Evaluation.recipientGroupID == groupID,
                    Evaluation.lotID == lotID,
                )
            )
        ).all()

        for eva in evals:
            remove_evaluation(eva.id)

        db.session.delete(entry)
        db.session.commit()
        return True
    return False
