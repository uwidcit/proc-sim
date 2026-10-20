from App.models import Admin
from App.database import db

def create_admin(username, password):
    newadmin = Admin(username=username, password=password)
    db.session.add(newadmin)
    db.session.commit()

def get_admin(id):
    return db.session.get(Admin, id)

def get_all_admins():
    return db.session.scalars(
        db.select(Admin)
    ).all()

def get_all_admins_json():
    admins = get_all_admins()
    if not admins:
        return []
    admins = [admin.get_json() for admin in admins]
    return admins