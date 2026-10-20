from App.models import LabType
from App.database import db


def create_lab_type(name, description):
    lab_type = LabType(name, description)
    db.session.add(lab_type)
    db.session.commit()
    return lab_type


def get_lab_type(id):
    return db.session.get(LabType, id)


def get_all_lab_types():
    return db.session.scalars(
        db.select(LabType).order_by(LabType.name)
    ).all()


def edit_lab_type(id, name=None, description=None):
    lab_type = get_lab_type(id)
    if lab_type:
        if name is not None:
            lab_type.name = name
        if description is not None:
            lab_type.description = description
        db.session.commit()
        return lab_type
    return None


def remove_lab_type(id):
    lab_type = get_lab_type(id)
    if lab_type:
        db.session.delete(lab_type)
        db.session.commit()
        return True
    return False
