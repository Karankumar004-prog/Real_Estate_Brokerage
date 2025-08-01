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
    # Conversion ratio: paid/total clients * 100
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

@admin_bp.route('/partners', methods=['GET', 'POST', 'DELETE', 'PUT'])
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
    elif request.method == 'PUT':
        data = request.form
        partner_id = data.get('id')
        partner = Partner.query.get(partner_id)
        if partner:
            partner.name = data['name']
            partner.phone = data['phone']
            partner.email = data['email']
            partner.type = data['type']
            partner.data = data['data']
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Partner not found'}), 404
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

@admin_bp.route('/export_partners_csv')
@login_required
@admin_required
def export_partners_csv():
    partners = Partner.query.all()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Name', 'Phone', 'Email', 'Type', 'Data'])
    for p in partners:
        writer.writerow([
            p.id,
            p.name or '',
            p.phone or '',
            p.email or '',
            p.type or '',
            p.data or ''
        ])
    output = io.BytesIO(si.getvalue().encode())
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='partners.csv')

@admin_bp.route('/export/partners')
@login_required
@admin_required
def export_partners():
    output = io.StringIO()
    output.write('id,name,phone,email,type,data\n')
    for p in Partner.query.all():
        output.write(f'{p.id},{p.name or ""},{p.phone or ""},{p.email or ""},{p.type or ""},{p.data or ""}\n')
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
            'is_active': getattr(e, 'is_active', True),
            'status': getattr(e, 'status', 'approved'),
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
            'is_active': a.is_active,
            'status': getattr(a, 'status', 'approved')
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
    # Only Admin1 can change any admin's password
    if password:
        if current_user.username == 'Admin1':
            user.set_password(password)
        # Other admins cannot change any admin's password
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
        if user.username == 'Admin1':
            return jsonify({'success': False, 'error': 'Admin1 is super Admin'}), 403
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
        if user.username == 'Admin1':
            return jsonify({'success': False, 'error': 'Admin1 is super Admin'}), 403
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
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    if not user or user.status != 'pending':
        return jsonify({'error': 'Invalid user'}), 400
    user.status = 'approved'
    # Update the notification
    notification = Notification.query.filter_by(user_id=user_id, type='admin_pending').first()
    if notification:
        notification.message = f"{user.username} Registered as Admin"
        notification.status = 'read'
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/notifications/deny', methods=['POST'])
@admin_required
def deny_admin():
    if not current_user.username == 'Admin1':
        return jsonify({'error': 'Unauthorized'}), 403
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    if not user or user.status != 'pending':
        return jsonify({'error': 'Invalid user'}), 400
    user.status = 'terminated'
    # Update the notification
    notification = Notification.query.filter_by(user_id=user_id, type='admin_pending').first()
    if notification:
        notification.message = f"{user.username} Permission is Terminated"
        notification.status = 'read'
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/notifications/unread_count')
@admin_required
def notifications_unread_count():
    if not current_user.username == 'Admin1':
        return jsonify({'error': 'Unauthorized'}), 403
    count = Notification.query.filter_by(status='unread').count()
    return jsonify({'unread_count': count})

@admin_bp.route('/notifications/mark_read', methods=['POST'])
@admin_required
def mark_notification_read():
    if not current_user.username == 'Admin1':
        return jsonify({'error': 'Unauthorized'}), 403
    notif_id = request.form.get('id')
    notification = Notification.query.get(notif_id)
    if notification:
        notification.status = 'read'
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Notification not found'}), 404

@admin_bp.route('/notifications/mark_all_read', methods=['POST'])
@admin_required
def mark_all_notifications_read():
    if not current_user.username == 'Admin1':
        return jsonify({'error': 'Unauthorized'}), 403
    Notification.query.filter_by(status='unread').update({'status': 'read'})
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/notifications/clear_all', methods=['POST'])
@admin_required
def clear_all_notifications():
    if not current_user.username == 'Admin1':
        return jsonify({'error': 'Unauthorized'}), 403
    Notification.query.delete()
    db.session.commit()
    return jsonify({'success': True})

# Client Management System Routes
@admin_bp.route('/clients/list')
@login_required
@admin_required
def clients_list():
    clients = Client.query.all()
    result = []
    for c in clients:
        employee = User.query.get(c.assigned_to) if c.assigned_to else None
        result.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'budget': c.budget,
            'area': c.area,
            'preferred_building': c.preferred_building,
            'status': c.status,
            'assigned_to': employee.username if employee else 'Unassigned',
            'assigned_to_id': c.assigned_to,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else '',
            'notes': getattr(c, 'notes', '')
        })
    return jsonify(result)

@admin_bp.route('/clients/statistics')
@login_required
@admin_required
def clients_statistics():
    total = Client.query.count()
    prospects = Client.query.filter_by(status='prospect').count()
    interested = Client.query.filter_by(status='interested').count()
    scheduled = Client.query.filter_by(status='visit_scheduled').count()
    booked = Client.query.filter_by(status='booked').count()
    paid = Client.query.filter_by(status='paid').count()
    
    return jsonify({
        'total': total,
        'prospects': prospects,
        'interested': interested,
        'scheduled': scheduled,
        'booked': booked,
        'paid': paid
    })

@admin_bp.route('/clients/add', methods=['POST'])
@login_required
@admin_required
def add_client():
    try:
        data = request.form
        client = Client(
            name=data['name'],
            phone=data['phone'],
            budget=data.get('budget', ''),
            area=data.get('area', ''),
            preferred_building=data.get('preferred_building', ''),
            status=data.get('status', 'prospect'),
            assigned_to=int(data['assigned_to']) if data.get('assigned_to') else None
        )
        db.session.add(client)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Client added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@admin_bp.route('/clients/update/<int:client_id>', methods=['POST'])
@login_required
@admin_required
def update_client(client_id):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'success': False, 'error': 'Client not found'}), 404
        
        data = request.form
        client.name = data['name']
        client.phone = data['phone']
        client.budget = data.get('budget', '')
        client.area = data.get('area', '')
        client.preferred_building = data.get('preferred_building', '')
        client.status = data.get('status', 'prospect')
        client.assigned_to = int(data['assigned_to']) if data.get('assigned_to') else None
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Client updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@admin_bp.route('/clients/delete/<int:client_id>', methods=['POST'])
@login_required
@admin_required
def delete_client(client_id):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'success': False, 'error': 'Client not found'}), 404
        
        client_name = client.name
        db.session.delete(client)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Client deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@admin_bp.route('/clients/details/<int:client_id>')
@login_required
@admin_required
def client_details(client_id):
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'success': False, 'error': 'Client not found'}), 404
    
    employee = User.query.get(client.assigned_to) if client.assigned_to else None
    
    return jsonify({
        'id': client.id,
        'name': client.name,
        'phone': client.phone,
        'budget': client.budget,
        'area': client.area,
        'preferred_building': client.preferred_building,
        'status': client.status,
        'assigned_to': employee.username if employee else 'Unassigned',
        'assigned_to_id': client.assigned_to,
        'created_at': client.created_at.strftime('%Y-%m-%d %H:%M') if client.created_at else '',
        'notes': getattr(client, 'notes', '')
    })

@admin_bp.route('/clients/export/csv')
@login_required
@admin_required
def export_clients_csv():
    clients = Client.query.all()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Name', 'Phone', 'Budget', 'Area', 'Preferred Building', 'Status', 'Assigned To', 'Created At'])
    
    for c in clients:
        employee = User.query.get(c.assigned_to) if c.assigned_to else None
        writer.writerow([
            c.id,
            c.name,
            c.phone,
            c.budget or '',
            c.area or '',
            c.preferred_building or '',
            c.status or '',
            employee.username if employee else 'Unassigned',
            c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ''
        ])
    
    output = io.BytesIO(si.getvalue().encode())
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='clients.csv')

@admin_bp.route('/clients/export/excel')
@login_required
@admin_required
def export_clients_excel():
    # This would require openpyxl library for Excel export
    # For now, return CSV with Excel mimetype
    return export_clients_csv()

@admin_bp.route('/employees/list/for-assignment')
@login_required
@admin_required
def employees_for_assignment():
    employees = User.query.filter_by(role='employee', is_active=True).all()
    result = []
    for e in employees:
        result.append({
            'id': e.id,
            'username': e.username,
            'mobile': e.mobile or '',
            'email': e.email or ''
        })
    return jsonify(result)

# Advanced Analytics Routes
@admin_bp.route('/analytics/performance')
@login_required
@admin_required
def performance_analytics():
    # Employee performance metrics
    employees = User.query.filter_by(role='employee').all()
    performance_data = []
    
    for emp in employees:
        client_count = Client.query.filter_by(assigned_to=emp.id).count()
        # Handle both lowercase and uppercase status values
        booked_count = Client.query.filter(
            Client.assigned_to == emp.id,
            Client.status.in_(['booked', 'Booked'])
        ).count()
        paid_count = Client.query.filter(
            Client.assigned_to == emp.id,
            Client.status.in_(['paid', 'Paid'])
        ).count()
        
        # Calculate conversion rate: (paid clients / total clients) * 100
        conversion_rate = (paid_count / client_count * 100) if client_count > 0 else 0
        
        performance_data.append({
            'employee': emp.username,
            'total_clients': client_count,
            'booked': booked_count,
            'paid': paid_count,
            'conversion_rate': round(conversion_rate, 1)
        })
    
    return jsonify(performance_data)

@admin_bp.route('/analytics/trends/detailed')
@login_required
@admin_required
def detailed_trends():
    # Detailed trend analysis
    from datetime import datetime, timedelta
    
    # Last 12 months data
    trends = []
    for i in range(12):
        date = datetime.now() - timedelta(days=30*i)
        month_start = date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        new_clients = Client.query.filter(
            Client.created_at >= month_start,
            Client.created_at <= month_end
        ).count()
        
        booked_clients = Client.query.filter(
            Client.status.in_(['booked', 'Booked']),
            Client.created_at >= month_start,
            Client.created_at <= month_end
        ).count()
        
        paid_clients = Client.query.filter(
            Client.status.in_(['paid', 'Paid']),
            Client.created_at >= month_start,
            Client.created_at <= month_end
        ).count()
        
        trends.append({
            'month': month_start.strftime('%B %Y'),
            'new_clients': new_clients,
            'booked': booked_clients,
            'paid': paid_clients
        })
    
    return jsonify(trends)

@admin_bp.route('/analytics/status-breakdown')
@login_required
@admin_required
def status_breakdown():
    # Client status breakdown - handle all possible status values
    status_mapping = {
        'Prospect': 'prospect',
        'prospect': 'prospect',
        'Interested': 'interested', 
        'interested': 'interested',
        'Schedule Visit': 'visit_scheduled',
        'visit_scheduled': 'visit_scheduled',
        'Booked': 'booked',
        'booked': 'booked',
        'Paid': 'paid',
        'paid': 'paid',
        'Completed': 'completed',
        'completed': 'completed',
        'Busy': 'busy',
        'Disagreed': 'disagreed',
        'Future Plans': 'future_plans'
    }
    
    breakdown = {}
    
    # Get all unique statuses from database
    all_statuses = db.session.query(Client.status).distinct().all()
    
    for status_tuple in all_statuses:
        status = status_tuple[0]
        if status:
            # Map to standardized status name
            normalized_status = status_mapping.get(status, status.lower())
            count = Client.query.filter_by(status=status).count()
            
            if normalized_status in breakdown:
                breakdown[normalized_status] += count
            else:
                breakdown[normalized_status] = count
    
    return jsonify(breakdown)

@admin_bp.route('/analytics/employee-comparison')
@login_required
@admin_required
def employee_comparison():
    # Compare employee performance
    employees = User.query.filter_by(role='employee').all()
    comparison = []
    
    for emp in employees:
        total_clients = Client.query.filter_by(assigned_to=emp.id).count()
        active_clients = Client.query.filter(
            Client.assigned_to == emp.id,
            Client.status.in_(['prospect', 'Prospect', 'interested', 'Interested', 'visit_scheduled', 'Schedule Visit'])
        ).count()
        successful_clients = Client.query.filter(
            Client.assigned_to == emp.id,
            Client.status.in_(['booked', 'Booked', 'paid', 'Paid', 'completed', 'Completed'])
        ).count()
        
        success_rate = (successful_clients / total_clients * 100) if total_clients > 0 else 0
        
        comparison.append({
            'employee': emp.username,
            'total_clients': total_clients,
            'active_clients': active_clients,
            'successful_clients': successful_clients,
            'success_rate': round(success_rate, 2)
        })
    
    return jsonify(comparison)

@admin_bp.route('/reports/generate')
@login_required
@admin_required
def generate_report():
    # Generate comprehensive report
    from datetime import datetime
    
    report_data = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_clients': Client.query.count(),
            'total_employees': User.query.filter_by(role='employee').count(),
            'total_admins': User.query.filter_by(role='admin').count(),
            'total_partners': Partner.query.count()
        },
        'client_status': {},
        'employee_performance': [],
        'recent_activity': []
    }
    
    # Client status breakdown
    statuses = ['prospect', 'Prospect', 'interested', 'Interested', 'visit_scheduled', 'Schedule Visit', 'booked', 'Booked', 'paid', 'Paid', 'completed', 'Completed']
    for status in statuses:
        count = Client.query.filter_by(status=status).count()
        # Normalize status name for reporting
        normalized_status = status.lower()
        if normalized_status in report_data['client_status']:
            report_data['client_status'][normalized_status] += count
        else:
            report_data['client_status'][normalized_status] = count
    
    # Employee performance
    employees = User.query.filter_by(role='employee').all()
    for emp in employees:
        client_count = Client.query.filter_by(assigned_to=emp.id).count()
        report_data['employee_performance'].append({
            'name': emp.username,
            'clients': client_count
        })
    
    # Recent activity (last 10 logs)
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    for log in recent_logs:
        report_data['recent_activity'].append({
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M'),
            'user': log.username,
            'action': log.action,
            'details': log.details
        })
    
    return jsonify(report_data)