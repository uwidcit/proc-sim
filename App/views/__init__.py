# blue prints are imported 
# explicitly instead of using *
from .user import user_views
from .index import index_views
from .auth import auth_views
from .student import student_views
from .admin import admin_views, setup_admin

views = [user_views, index_views, auth_views, student_views, admin_views]
# blueprints must be added to this list