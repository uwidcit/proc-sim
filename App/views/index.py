from flask import Blueprint, render_template, jsonify, redirect, request, url_for, flash
from flask_jwt_extended import jwt_required, current_user
from functools import wraps

from App.controllers.academic_year import set_current_year, is_valid_year

index_views = Blueprint('index_views', __name__, template_folder='../templates')


def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        if not current_user or not current_user.is_admin():
            flash("Admin access required", "failed")
            return redirect(url_for('index_views.index_page'))
        return f(*args, **kwargs)
    return decorated


@index_views.route('/', methods=['GET'])
def index_page():
    return render_template('index.html')


@index_views.route('/set-academic-year', methods=['POST'])
@admin_required
def set_academic_year():
    year = request.form.get('year')
    if not is_valid_year(year):
        flash('Invalid academic year', 'failed')
    else:
        set_year = set_current_year(year)
        if set_year:
            flash(f'Current academic year set to {set_year} for all students', 'success')
        else:
            flash('Could not update academic year', 'failed')
    next_url = request.form.get('next') or request.referrer or url_for('index_views.index_page')
    return redirect(next_url)


@index_views.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})


@index_views.route('/healthcheck', methods=['GET'])
def health_check_alias():
    return jsonify({'status': 'healthy'})
