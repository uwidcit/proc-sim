from App.models import Lot, LotGroup
from App.database import db
from .academic_year import get_current_year


def create_lot(labType, labSize, budget, labTypeId=None, academic_year=None, numMachines=0):
    if academic_year is None:
        academic_year = get_current_year()
    newlot = Lot(
        labType,
        labSize,
        budget,
        academic_year=academic_year,
        numMachines=numMachines,
    )
    if labTypeId is not None:
        newlot.labTypeId = labTypeId
    db.session.add(newlot)
    db.session.flush()
    newlot.set_generated_name()
    db.session.commit()
    return newlot


def get_lot(id):
    return db.session.get(Lot, id)


def get_all_lots(academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(Lot).filter_by(academic_year=academic_year)
    ).all()


def get_all_lots_json(academic_year=None):
    lots = get_all_lots(academic_year=academic_year)
    if not lots:
        return []
    return [lot.get_json() for lot in lots]


def edit_lot(id, labType=None, labTypeId=None, labSize=None, budget=None, numMachines=None):
    lot = get_lot(id)
    if lot:
        if labType:
            lot.labType = labType
        if labTypeId is not None:
            lot.labTypeId = labTypeId
        if labSize is not None:
            lot.labSize = labSize
        if budget is not None and budget != "":
            lot.budget = budget
        if numMachines is not None and numMachines != "":
            lot.numMachines = int(numMachines)
        db.session.commit()


def edit_lotRFP_details(id, deviceType=None, resolution=None, os=None, cpu=None, ram=None, drive=None, gpu=None, peripherals=None, features=None, io=None):
    lot = get_lot(id)
    if lot:
        if deviceType is not None:
            lot.deviceType = deviceType
        if resolution is not None:
            lot.resolution = resolution
        if os is not None:
            lot.os = os
        if cpu is not None:
            lot.cpu = cpu
        if ram is not None:
            lot.ram = ram
        if drive is not None:
            lot.drive = drive
        if gpu is not None:
            lot.gpu = gpu
        if peripherals is not None:
            lot.peripherals = peripherals
        if features is not None:
            lot.features = features
        if io is not None:
            lot.io = io

        db.session.commit()
        return lot
    return None


def get_lotRFP_details_json(id):
    lot = get_lot(id)
    if lot:
        return {
            "deviceType": lot.deviceType,
            "resolution": lot.resolution,
            "os": lot.os,
            "cpu": lot.cpu,
            "ram": lot.ram,
            "drive": lot.drive,
            "gpu": lot.gpu,
            "peripherals": lot.peripherals,
            "features": lot.features,
            "io": lot.io,
        }
    return None


def remove_lot(id):
    from .group import remove_group

    lot = get_lot(id)
    if lot:
        assigned = db.session.scalars(
            db.select(LotGroup).filter_by(lotID=lot.id)
        ).first()

        if not assigned:
            db.session.delete(lot)
            db.session.commit()
            return True
        else:
            remove_group(assigned.groupID)
            db.session.delete(lot)
            db.session.commit()
    return False
