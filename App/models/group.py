from App.database import db
from App.academic_years import DEFAULT_ACADEMIC_YEAR


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Wide enough for "G{n} " prefix + up to 40-char display name
    groupName = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="requested")
    academic_year = db.Column(db.Integer, nullable=False, default=DEFAULT_ACADEMIC_YEAR, index=True)

    __table_args__ = (
        db.UniqueConstraint("groupName", "academic_year", name="uq_group_name_year"),
    )

    def __init__(self, groupName, academic_year=None):
        self.groupName = groupName
        self.academic_year = academic_year if academic_year is not None else DEFAULT_ACADEMIC_YEAR

    def set_generated_name(self, number):
        """Prefix the current display name with G{number} (year-scoped label)."""
        self.groupName = f"G{int(number)} {self.groupName}"

    def get_json(self):
        return {
            "id": self.id,
            "groupName": self.groupName,
            "status": self.status,
            "academic_year": self.academic_year,
        }
