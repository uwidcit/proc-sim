from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user as jwt_current_user
from functools import wraps

from App.controllers import (
    create_user,
    get_all_users_json,
)

user_views = Blueprint("user_views", __name__, template_folder="../templates")


def admin_api_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        if not jwt_current_user or not jwt_current_user.is_admin():
            return jsonify(message="Admin access required"), 403
        return f(*args, **kwargs)

    return decorated


@user_views.route("/api/users", methods=["GET"])
@admin_api_required
def get_users_action():
    return jsonify(get_all_users_json())


@user_views.route("/api/users", methods=["POST"])
@admin_api_required
def create_user_endpoint():
    data = request.json or {}
    user = create_user(data["username"], data["password"])
    return jsonify({"message": f"user {user.username} created with id {user.id}"})
