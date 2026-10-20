from App.database import db


class AppSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_size_min = db.Column(db.Integer, nullable=False, default=3)
    group_size_max = db.Column(db.Integer, nullable=False, default=3)

    def get_json(self):
        return {
            "group_size_min": self.group_size_min,
            "group_size_max": self.group_size_max,
        }
