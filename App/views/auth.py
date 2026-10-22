from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies

from App.controllers import (
    login,
    register_student,
)

auth_views = Blueprint('auth_views', __name__, template_folder='../templates')


'''
Page/Action Routes
'''

@auth_views.route('/identify', methods=['GET'])
@jwt_required()
def identify_page():
    return render_template('message.html', title="Identify", message=f"You are logged in as {current_user.id} - {current_user.username}")


@auth_views.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        student, err = register_student(
            name=request.form.get('name'),
            student_id=request.form.get('student_id'),
            password=request.form.get('password'),
            confirm_password=request.form.get('confirm_password'),
            email=request.form.get('email'),
        )
        if err:
            flash(err, "failed")
            return render_template(
                'register.html',
                name=request.form.get('name', ''),
                student_id=request.form.get('student_id', ''),
                email=request.form.get('email', ''),
            )

        user, token, role = login(student.username, request.form.get('password'))
        flash("Account claimed. Welcome!", "success")
        response = redirect('/student')
        set_access_cookies(response, token)
        return response

    return render_template('register.html')


@auth_views.route('/login', methods=['POST'])
def login_action():
    data = request.form
    user, token, role = login(data['username'], data['password']) 

    if not token:
        flash('Bad username or password given', "failed")
        return redirect(request.referrer) 

    flash('Login Successful', "success")

    name = user.username if user.is_admin() else user.name
    flash(f"Welcome {name}", "success")
    
    if role == "student":
        response = redirect('/student')
    elif role == "admin":
        response = redirect('/admin/lab-types')
    else:
        response = redirect('/')  

    set_access_cookies(response, token)
    return response

@auth_views.route('/logout', methods=['GET'])
def logout_action():
    response = redirect(url_for('index_views.index_page')) 
    flash("Logged Out!", "success")
    unset_jwt_cookies(response)
    return response

'''
API Routes
'''

@auth_views.route('/api/login', methods=['POST'])
def user_login_api():
  data = request.json
  user, token, role = login(data['username'], data['password'])
  if not token:
    return jsonify(message='bad username or password given'), 401
  response = jsonify(access_token=token, role=role, username=user.username)
  set_access_cookies(response, token)
  return response

@auth_views.route('/api/identify', methods=['GET'])
@jwt_required()
def identify_user():
    return jsonify({'message': f"username: {current_user.username}, id : {current_user.id}"})

@auth_views.route('/api/logout', methods=['GET'])
def logout_api():
    response = jsonify(message="Logged Out!")
    unset_jwt_cookies(response)
    return response