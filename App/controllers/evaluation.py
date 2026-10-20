from App.models import Evaluation, Lot
from App.database import db
from .academic_year import get_current_year

def create_evaluation(sourceGroupID, recipientGroupID, bidID, lotID, specsMet, presentation, professionalism, budget):
    neweval = Evaluation(sourceGroupID, recipientGroupID, bidID, lotID, specsMet, presentation, professionalism, budget)
    db.session.add(neweval)
    db.session.commit()
    return neweval

def edit_evaluation(id, specsMet, presentation, professionalism, budget, specsSelected=None, deviceType=None, resolution=None, os=None, cpu=None, ram=None, drive=None, gpu=None, peripherals=None, features=None, io=None):
    eva = get_evaluation(id)
    if eva:
        eva.overallScore = round((((specsMet + presentation + professionalism + budget)/25) * 10), 1)

        if specsMet is not None:
            eva.specsMet = specsMet
        if presentation is not None:
            eva.presentation = presentation
        if professionalism is not None:
            eva.professionalism = professionalism
        if budget is not None:
            eva.budget = budget
        if specsSelected is not None:
            eva.specsSelected = specsSelected
        if deviceType is not None:
            eva.deviceType = deviceType
        if resolution is not None:
            eva.resolution = resolution
        if os is not None:
            eva.os = os
        if cpu is not None:
            eva.cpu = cpu
        if ram is not None:
            eva.ram = ram
        if drive is not None:
            eva.drive = drive
        if gpu is not None:
            eva.gpu = gpu
        if peripherals is not None:
            eva.peripherals = peripherals
        if features is not None:
            eva.features = features
        if io is not None:
            eva.io = io

        db.session.commit()
        return True
    return False

def select_evaluation(id):
    evaluation = get_evaluation(id)
    evaluation.status = "selected"
    db.session.commit()

def get_evaluation(id):
    return db.session.get(Evaluation, id)

def get_all_evaluations(academic_year=None):
    if academic_year is None:
        academic_year = get_current_year()
    return db.session.scalars(
        db.select(Evaluation)
        .join(Lot, Lot.id == Evaluation.lotID)
        .filter(Lot.academic_year == academic_year)
    ).all()

def get_all_evaluations_json(academic_year=None):
    evals = get_all_evaluations(academic_year=academic_year)
    if not evals:
        return []
    evals = [eva.get_json() for eva in evals]
    return evals

def remove_evaluation(id):
    eva = get_evaluation(id)
    if eva:
        db.session.delete(eva)
        db.session.commit()
        return True
    return False