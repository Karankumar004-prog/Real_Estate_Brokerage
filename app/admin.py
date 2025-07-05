from flask import Blueprint, render_template, jsonify, request, send_file
from flask_login import login_required, current_user
from .auth import admin_required
from .models import db, User, Client, Partner, ActivityLog, Notification
import io
import csv
from sqlalchemy import func, desc
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/analytics/summary')
@login_required
@admin_required
def analytics_summary():
    # Total clients (only those assigned to an employee)
    total_clients = Client.query.filter(Client.assigned_to.isnot(None)).count()
    # Total employees
    num_employees = User.query.filter_by(role='employee').count()
    # Top buildings/areas by number of assigned employees
    top_buildings = db.session.query(Client.preferred_building, func.count(Client.assigned_to)) \
        .filter(Client.assigned_to.isnot(None)) \
        .group_by(Client.preferred_building) \
        .order_by(desc(func.count(Client.assigned_to))) \
        .limit(3).all()
    top_buildings_list = [b[0] for b in top_buildings]
    # Most requested budget range
    budgets = db.session.query(Client.budget, func.count(Client.id)).filter(Client.assigned_to.isnot(None)).group_by(Client.budget).order_by(desc(func.count(Client.id))).all()
    most_requested_budget = str(budgets[0][0]) if budgets else '-'
    # Conversion ratio: paid/total
    paid_count = Client.query.filter(Client.status.ilike('%paid%'), Client.assigned_to.isnot(None)).count()
    conversion_ratio = f"{int((paid_count/total_clients)*100) if total_clients else 0}%"
    # Revenue: count of 'paid' clients * 1 (stub, replace with real revenue logic)
    revenue = Client.query.filter(Client.status.ilike('%paid%'), Client.assigned_to.isnot(None)).count() * 1000000  # Example: 10L per paid client
    # Top employees by number of clients
    top_employees = db.session.query(User.username, func.count(Client.id)) \
        .join(Client, Client.assigned_to == User.id) \
        .filter(User.role == 'employee') \
        .group_by(User.username) \
        .order_by(desc(func.count(Client.id))) \
        .limit(5).all()
    top_employees_list = [e[0] for e in top_employees]
    num_admins = User.query.filter_by(role='admin').count()
    return jsonify({
        'total_clients': total_clients,
        'num_employees': num_employees,
        'top_buildings': top_buildings_list,
        'most_requested_budget': most_requested_budget,
        'conversion_ratio': conversion_ratio,
        'revenue': f"₹{revenue/100000:,.2f}L",  # Example formatting
        'top_employees': top_employees_list,
        'num_admins': num_admins
    })

@admin_bp.route('/analytics/trends')
@login_required
@admin_required
def analytics_trends():
    # Example: monthly new clients
    year = datetime.now().year
    monthly_counts = [0] * 12
    clients = Client.query.all()
    for c in clients:
        if c.created_at and c.created_at.year == year:
            monthly_counts[c.created_at.month - 1] += 1
    labels = [datetime.strftime(datetime(1, i+1, 1), '%b') for i in range(12)]
    return jsonify({'labels': labels, 'values': monthly_counts})

@admin_bp.route('/analytics/agreed_stats')
@login_required
@admin_required
def analytics_agreed_stats():
    agreed = Client.query.filter(Client.status.ilike('%agreed%')).count()
    not_agreed = Client.query.filter(~Client.status.ilike('%agreed%')).count()
    return jsonify({'agreed': agreed, 'not_agreed': not_agreed})

@admin_bp.route('/analytics/top_employees')
@login_required
@admin_required
def analytics_top_employees():
    top_employees = db.session.query(User.username, func.count(Client.id)) \
        .join(Client, Client.assigned_to == User.id) \
        .filter(User.role == 'employee') \
        .group_by(User.username) \
        .order_by(desc(func.count(Client.id))) \
        .limit(5).all()
    labels = [e[0] for e in top_employees]
    values = [e[1] for e in top_employees]
    return jsonify({'labels': labels, 'values': values})

@admin_bp.route('/partners', methods=['GET', 'POST', 'DELETE'])
@login_required
@admin_required
def partners():
    if request.method == 'GET':
        partners = Partner.query.all()
        return jsonify([
            {
                'id': p.id,
                'name': p.name,
                'phone': p.phone,
                'email': p.email,
                'type': p.type,
                'data': p.data
            }
            for p in partners
        ])
    elif request.method == 'POST':
        data = request.form
        partner = Partner(
            name=data['name'],
            phone=data['phone'],
            email=data['email'],
            type=data['type'],
            data=data['data']
        )
        db.session.add(partner)
        db.session.commit()
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        partner_id = request.form.get('id')
        partner = Partner.query.get(partner_id)
        if partner:
            db.session.delete(partner)
            db.session.commit()
        return jsonify({'success': True})

@admin_bp.route('/export/clients')
@login_required
@admin_required
def export_clients():
    output = io.StringIO()
    output.write('id,name,phone,assigned_to\n')
    for c in Client.query.all():
        output.write(f'{c.id},{c.name},{c.phone},{c.assigned_to}\n')
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='clients.csv')

@admin_bp.route('/export/partners')
@login_required
@admin_required
def export_partners():
    output = io.StringIO()
    output.write('id,type,data\n')
    for p in Partner.query.all():
        data = p.encrypted_data.decode() if isinstance(p.encrypted_data, bytes) else p.encrypted_data
        output.write(f'{p.id},{p.type},{data}\n')
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='partners.csv')

@admin_bp.route('/employees/list')
@login_required
@admin_required
def employees_list():
    employees = User.query.filter_by(role='employee').all()
    result = []
    for e in employees:
        clients = Client.query.filter_by(assigned_to=e.id).all()
        client_list = [
            {
                'id': c.id,
                'name': c.name,
                'phone': c.phone,
                'status': c.status,
                'preferred_building': c.preferred_building
            } for c in clients
        ]
        result.append({
            'id': e.id,
            'username': e.username,
            'mobile': getattr(e, 'mobile', ''),
            'email': getattr(e, 'email', ''),
            'joining_date': getattr(e, 'joining_date', ''),
            'leaving_date': getattr(e, 'leaving_date', ''),
            'address': getattr(e, 'address', ''),
            'aadhaar_number': getattr(e, 'aadhaar_number', ''),
            'aadhaar_image': getattr(e, 'aadhaar_image', ''),
            'clients': client_list
        })
    return jsonify(result) 

@admin_bp.route('/employees/delete', methods=['POST'])
@login_required
@admin_required
def delete_employee():
    emp_id = request.form.get('id')
    user = User.query.get(emp_id)
    if user and user.role == 'employee':
        # Delete all clients assigned to this employee
        Client.query.filter_by(assigned_to=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Employee not found'}), 404

@admin_bp.route('/employees/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_employee_active():
    emp_id = request.form.get('id')
    user = User.query.get(emp_id)
    if user and user.role == 'employee':
        user.is_active = not user.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': user.is_active})
    return jsonify({'success': False, 'error': 'Employee not found'}), 404 

@admin_bp.route('/employees/update', methods=['POST'])
@login_required
@admin_required
def update_employee():
    emp_id = request.form.get('id')
    user = User.query.get(emp_id)
    if not user or user.role != 'employee':
        return jsonify({'success': False, 'error': 'Employee not found'}), 404
    # Update mandatory fields
    user.mobile = request.form.get('mobile')
    user.email = request.form.get('email')
    user.address = request.form.get('address')
    user.aadhaar_number = request.form.get('aadhaar_number')
    # Optional fields
    joining_date = request.form.get('joining_date')
    leaving_date = request.form.get('leaving_date')
    if joining_date:
        if isinstance(joining_date, str):
            user.joining_date = datetime.strptime(joining_date, '%Y-%m-%d').date()
        else:
            user.joining_date = joining_date
    if leaving_date:
        if isinstance(leaving_date, str):
            user.leaving_date = datetime.strptime(leaving_date, '%Y-%m-%d').date()
        else:
            user.leaving_date = leaving_date
    password = request.form.get('password')
    if password:
        user.set_password(password)
    # Aadhaar image upload
    if 'aadhaar_image' in request.files and request.files['aadhaar_image'].filename:
        from werkzeug.utils import secure_filename
        import os
        file = request.files['aadhaar_image']
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'aadhaar_uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        user.aadhaar_image = os.path.relpath(file_path, start=os.path.dirname(os.path.dirname(__file__)))
    db.session.commit()
    return jsonify({'success': True}) 

@admin_bp.route('/export_activity_logs_csv')
@login_required
@admin_required
def export_activity_logs_csv():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'User', 'Action', 'Timestamp', 'Details'])
    for log in logs:
        writer.writerow([
            log.id,
            log.username or '',
            log.action,
            log.timestamp,
            log.details or ''
        ])
    output = io.BytesIO(si.getvalue().encode())
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='activity_logs.csv')

@admin_bp.route('/employees/export_csv')
@login_required
@admin_required
def export_employees_csv():
    employees = User.query.filter_by(role='employee').all()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Username', 'Mobile', 'Email', 'Address', 'Aadhaar Number', 'Aadhaar Image', 'Joining Date', 'Leaving Date', 'Is Active'])
    for e in employees:
        writer.writerow([
            e.id,
            e.username,
            e.mobile or '',
            e.email or '',
            e.address or '',
            e.aadhaar_number or '',
            e.aadhaar_image or '',
            e.joining_date or '',
            e.leaving_date or '',
            'Active' if e.is_active else 'Deactive'
        ])
    output = io.BytesIO(si.getvalue().encode())
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='employees.csv')

@admin_bp.route('/export_admins_csv')
@login_required
@admin_required
def export_admins_csv():
    admins = User.query.filter_by(role='admin').all()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Username', 'Mobile', 'Email', 'Address', 'Joining Date', 'Leaving Date'])
    for a in admins:
        writer.writerow([
            a.id,
            a.username,
            a.mobile or '',
            a.email or '',
            a.address or '',
            a.joining_date or '',
            a.leaving_date or ''
        ])
    output = io.BytesIO(si.getvalue().encode())
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='admins.csv')

@admin_bp.route('/admins/list')
@login_required
@admin_required
def admins_list():
    admins = User.query.filter_by(role='admin').all()
    result = []
    for a in admins:
        result.append({
            'id': a.id,
            'username': a.username,
            'mobile': getattr(a, 'mobile', ''),
            'email': getattr(a, 'email', ''),
            'address': getattr(a, 'address', ''),
            'aadhaar_number': getattr(a, 'aadhaar_number', ''),
            'aadhaar_image': getattr(a, 'aadhaar_image', ''),
            'joining_date': str(a.joining_date) if a.joining_date else '',
            'leaving_date': str(a.leaving_date) if a.leaving_date else '',
            'is_active': a.is_active
        })
    return jsonify(result)

@admin_bp.route('/admins/update', methods=['POST'])
@login_required
@admin_required
def update_admin():
    admin_id = request.form.get('id')
    user = User.query.get(admin_id)
    if not user or user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin not found'}), 404
    user.mobile = request.form.get('mobile')
    user.email = request.form.get('email')
    user.address = request.form.get('address')
    user.aadhaar_number = request.form.get('aadhaar_number')
    joining_date = request.form.get('joining_date')
    leaving_date = request.form.get('leaving_date')
    if joining_date:
        if isinstance(joining_date, str):
            user.joining_date = datetime.strptime(joining_date, '%Y-%m-%d').date()
        else:
            user.joining_date = joining_date
    if leaving_date:
        if isinstance(leaving_date, str):
            user.leaving_date = datetime.strptime(leaving_date, '%Y-%m-%d').date()
        else:
            user.leaving_date = leaving_date
    password = request.form.get('password')
    # Only Admin1 can change their own password
    if user.username == 'Admin1':
        if current_user.username == 'Admin1' and password:
            user.set_password(password)
    else:
        if password:
            user.set_password(password)
    # Aadhaar image upload
    if 'aadhaar_image' in request.files and request.files['aadhaar_image'].filename:
        from werkzeug.utils import secure_filename
        import os
        file = request.files['aadhaar_image']
        ext = os.path.splitext(secure_filename(file.filename))[1]
        filename = f"{user.aadhaar_number}{ext}"
        upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'aadhaar_uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        user.aadhaar_image = os.path.relpath(file_path, start=os.path.dirname(os.path.dirname(__file__)))
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/admins/delete', methods=['POST'])
@login_required
@admin_required
def delete_admin():
    admin_id = request.form.get('id')
    user = User.query.get(admin_id)
    if user and user.role == 'admin':
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Admin not found'}), 404

@admin_bp.route('/admins/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_admin_active():
    admin_id = request.form.get('id')
    user = User.query.get(admin_id)
    if user and user.role == 'admin':
        user.is_active = not user.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': user.is_active})
    return jsonify({'success': False, 'error': 'Admin not found'}), 404

@admin_bp.route('/activity_logs/json')
@login_required
@admin_required
def activity_logs_json():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(50).all()
    return jsonify([
        {
            'id': log.id,
            'username': log.username,
            'action': log.action,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'details': log.details
        }
        for log in logs
    ])

@admin_bp.route('/notifications', methods=['GET'])
@admin_required
def get_notifications():
    if not current_user.username == 'Admin1':
        return jsonify({'error': 'Unauthorized'}), 403
    notifications = Notification.query.order_by(Notification.timestamp.desc()).all()
    notif_list = [
        {
            'id': n.id,
            'message': n.message,
            'type': n.type,
            'user_id': n.user_id,
            'status': n.status,
            'timestamp': n.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for n in notifications
    ]
    return jsonify(notif_list)

@admin_bp.route('/notifications/approve', methods=['POST'])
@admin_required
def approve_admin():
    if not current_user.username == 'Admin1':
        return jsonify({'error': 'Unauthorized'}), 403
    notif_id = request.form.get('notif_id')
    notification = Notification.query.get(notif_id)
    if not notification or notification.type != 'admin_pending':
        return jsonify({'error': 'Invalid notification'}), 400
    user = User.query.get(notification.user_id)
    if not user or user.status != 'pending':
        return jsonify({'error': 'Invalid user'}), 400
    user.status = 'approved'
    notification.message = f"{user.username} Registered as Admin"
    notification.status = 'read'
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/notifications/deny', methods=['POST'])
@admin_required
def deny_admin():
    if not current_user.username == 'Admin1':
        return jsonify({'error': 'Unauthorized'}), 403
    notif_id = request.form.get('notif_id')
    notification = Notification.query.get(notif_id)
    if not notification or notification.type != 'admin_pending':
        return jsonify({'error': 'Invalid notification'}), 400
    user = User.query.get(notification.user_id)
    if not user or user.status != 'pending':
        return jsonify({'error': 'Invalid user'}), 400
    user.status = 'terminated'
    notification.message = f"{user.username} Permission is Terminated"
    notification.status = 'read'
    db.session.commit()
    return jsonify({'success': True})