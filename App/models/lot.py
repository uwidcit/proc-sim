from App.database import db
from App.academic_years import DEFAULT_ACADEMIC_YEAR


class Lot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10))
    labType = db.Column(db.String(30), nullable=False)
    labTypeId = db.Column(db.Integer, db.ForeignKey("lab_type.id"), nullable=True)
    labTypeObj = db.relationship("LabType", foreign_keys=[labTypeId], lazy="joined")
    # Size category only (Small / Medium / Large / Extra Large) — not machine count
    labSize = db.Column(db.String(30), nullable=False, default="")
    numMachines = db.Column(db.Integer, nullable=False, default=0)
    budget = db.Column(db.Float, nullable=False)
    academic_year = db.Column(db.Integer, nullable=False, default=DEFAULT_ACADEMIC_YEAR, index=True)
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

    def __init__(self, labType, labSize, budget, academic_year=None, numMachines=0):
        self.labType = labType
        self.labSize = labSize or ""
        self.budget = budget
        self.numMachines = int(numMachines or 0)
        self.academic_year = academic_year if academic_year is not None else DEFAULT_ACADEMIC_YEAR

    def set_generated_name(self):
        self.name = f"Lot {self.id}"

    def get_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "labType": self.labType,
            "labSize": self.labSize,
            "numMachines": self.numMachines,
            "budget": self.budget,
            "academic_year": self.academic_year,
        }
