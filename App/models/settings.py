from App.database import db
from App.academic_years import DEFAULT_ACADEMIC_YEAR


class AppSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_size_min = db.Column(db.Integer, nullable=False, default=3)
    group_size_max = db.Column(db.Integer, nullable=False, default=3)
    # Year students work under (admin-configured)
    active_academic_year = db.Column(
        db.Integer, nullable=False, default=DEFAULT_ACADEMIC_YEAR
    )
    # When false, vendors cannot see Accepted/Rejected award outcomes
    results_published = db.Column(db.Boolean, nullable=False, default=False)

    def get_json(self):
        return {
            "group_size_min": self.group_size_min,
            "group_size_max": self.group_size_max,
            "active_academic_year": self.active_academic_year,
            "results_published": bool(self.results_published),
        }
