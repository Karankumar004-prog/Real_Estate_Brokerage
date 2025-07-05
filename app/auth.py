from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, log_activity, Notification
from . import db, login_manager
from functools import wraps
import os
from werkzeug.utils import secure_filename
from flask import current_app
from datetime import date

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.status == 'pending':
                flash('Your admin registration is still pending approval.')
                return render_template('login.html')
            if user.status == 'terminated':
                flash('Your admin registration was denied. Permission is terminated.')
                return render_template('login.html')
            if not user.is_active:
                flash('Your account has been deactivated.')
                return render_template('login.html')
            if user.leaving_date and user.leaving_date < date.today():
                flash('Your account is no longer active (left company).')
                return render_template('login.html')
            login_user(user)
            log_activity(user, 'login', 'User logged in successfully')
            flash('Logged in successfully.')
            return redirect(url_for('admin.dashboard') if user.role == 'admin' else url_for('employee.dashboard'))
        else:
            flash('Invalid Username or password.')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_activity(current_user, 'logout', 'User logged out')
    logout_user()
    flash('Logged out successfully.')
    response = redirect(url_for('auth.login'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        aadhaar_number = request.form.get('aadhaar_number')
        aadhaar_image_file = request.files.get('aadhaar_image')
        # Check for existing user
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
        else:
            user = User(username=username)
            if password:
                user.set_password(password)
            if role:
                user.role = role
            if phone:
                user.mobile = phone
            if email:
                user.email = email
            if address:
                user.address = address
            if aadhaar_number:
                user.aadhaar_number = aadhaar_number
            if aadhaar_image_file and aadhaar_image_file.filename:
                user.aadhaar_image = relative_image_path
            # Set status and notification logic
            if role == 'admin':
                user.status = 'pending'
                notif_msg = f"{username} trying to register as an Admin. Authorization is valid?"
                notif_type = 'admin_pending'
            else:
                user.status = 'approved'
                notif_msg = f"{username} has registered as an Employee"
                notif_type = 'employee_registered'
            db.session.add(user)
            db.session.commit()
            # Find superadmin (Admin1)
            superadmin = User.query.filter_by(username='Admin1', role='admin').first()
            if superadmin:
                notification = Notification(
                    message=notif_msg,
                    type=notif_type,
                    user_id=user.id
                )
                db.session.add(notification)
                db.session.commit()
            log_activity(user, 'register', 'User registered successfully')
            if role == 'admin':
                flash('Registration request submitted. Awaiting superadmin approval.')
                return redirect(url_for('auth.login'))
            else:
                flash('Registration successful')
                return redirect(url_for('auth.login'))
    return render_template('register.html') 