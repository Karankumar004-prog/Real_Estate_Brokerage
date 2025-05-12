from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from .models import Client, Reminder
from . import db
from datetime import datetime, timedelta
from .utils import export_to_csv
import io
from sqlalchemy import extract

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/dashboard')
@login_required
def dashboard():
    total_clients = Client.query.filter_by(assigned_to=current_user.id).count()
    visits_scheduled = Client.query.filter(Client.assigned_to==current_user.id, Client.status.ilike('schedule visit')).count()
    booked = Client.query.filter(Client.assigned_to==current_user.id, Client.status.ilike('booked')).count()
    reminders = Reminder.query.filter_by(employee_id=current_user.id, is_sent=False).order_by(Reminder.remind_at).limit(5).all()
    return render_template('employee/dashboard.html',
        total_clients=total_clients,
        visits_scheduled=visits_scheduled,
        booked=booked,
        reminders=reminders,
        employee_name=current_user.username
    )

@employee_bp.route('/clients')
@login_required
def clients():
    search = request.args.get('search', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    query = Client.query.filter_by(assigned_to=current_user.id)
    if search:
        query = query.filter(Client.name.ilike(f'%{search}%'))
    if start_date:
        query = query.filter(Client.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Client.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    clients = query.all()
    return render_template('employee/clients.html', clients=clients, search=search)

@employee_bp.route('/clients/add', methods=['POST'])
@login_required
def add_client():
    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')
    budget = data.get('budget')
    area = data.get('area')
    preferred_building = data.get('preferred_building')
    status = data.get('status')
    client = Client(
        name=name,
        phone=phone,
        budget=budget,
        area=area,
        preferred_building=preferred_building,
        assigned_to=current_user.id,
        status=status
    )
    db.session.add(client)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Client added successfully.'})

@employee_bp.route('/clients/edit/<int:client_id>', methods=['POST'])
@login_required
def edit_client(client_id):
    client = Client.query.filter_by(id=client_id, assigned_to=current_user.id).first_or_404()
    data = request.get_json()
    client.name = data.get('name')
    client.phone = data.get('phone')
    client.budget = data.get('budget')
    client.area = data.get('area')
    client.preferred_building = data.get('preferred_building')
    client.status = data.get('status')
    db.session.commit()
    return jsonify({'success': True, 'message': 'Client updated successfully.'})

@employee_bp.route('/clients/delete/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.filter_by(id=client_id, assigned_to=current_user.id).first_or_404()
    db.session.delete(client)
    db.session.commit()
    flash('Client deleted successfully.')
    return redirect(url_for('employee.clients'))

@employee_bp.route('/clients/<int:client_id>')
@login_required
def client_detail(client_id):
    client = Client.query.filter_by(id=client_id, assigned_to=current_user.id).first_or_404()
    return render_template('employee/client_detail.html', client=client)

@employee_bp.route('/clients/export_csv')
@login_required
def export_clients_csv():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    query = Client.query.filter_by(assigned_to=current_user.id)
    if start_date:
        query = query.filter(Client.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Client.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    clients = query.all()
    output = io.StringIO()
    export_to_csv(clients, output)
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='clients.csv'
    )

@employee_bp.route('/clients/update_status/<int:client_id>', methods=['POST'])
@login_required
def update_client_status(client_id):
    client = Client.query.filter_by(id=client_id, assigned_to=current_user.id).first_or_404()
    status = request.form.get('status')
    if status:
        client.status = status
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'No status provided'}), 400

# Reminders
@employee_bp.route('/reminders')
@login_required
def reminders():
    reminders = Reminder.query.filter_by(employee_id=current_user.id, is_sent=False).order_by(Reminder.remind_at).all()
    return render_template('employee/reminders.html', reminders=reminders)

@employee_bp.route('/reminders/add/<int:client_id>', methods=['GET', 'POST'])
@login_required
def add_reminder(client_id):
    client = Client.query.filter_by(id=client_id, assigned_to=current_user.id).first_or_404()
    if request.method == 'POST':
        remind_at = request.form['remind_at']
        message = request.form['message']
        reminder = Reminder(
            client_id=client.id,
            employee_id=current_user.id,
            remind_at=datetime.strptime(remind_at, '%Y-%m-%dT%H:%M'),
            message=message
        )
        db.session.add(reminder)
        db.session.commit()
        flash('Reminder added successfully.')
        return redirect(url_for('employee.reminders'))
    return render_template('employee/add_reminder.html', client=client)

@employee_bp.route('/reminders/mark_done/<int:reminder_id>', methods=['POST'])
@login_required
def mark_reminder_done(reminder_id):
    reminder = Reminder.query.filter_by(id=reminder_id, employee_id=current_user.id).first_or_404()
    reminder.is_sent = True
    db.session.commit()
    flash('Reminder marked as done.')
    return redirect(url_for('employee.reminders'))

# JSON endpoints for popups/analytics
@employee_bp.route('/clients/all/json')
@login_required
def all_clients_json():
    clients = Client.query.filter_by(assigned_to=current_user.id).all()
    return jsonify([{
        'date': c.created_at.strftime('%Y-%m-%d') if c.created_at else '',
        'name': c.name,
        'phone': c.phone,
        'budget': c.budget,
        'area': c.area,
        'preferred_building': c.preferred_building,
        'status': c.status
    } for c in clients])

@employee_bp.route('/clients/visits_scheduled/json')
@login_required
def visits_scheduled_clients_json():
    clients = Client.query.filter(Client.assigned_to==current_user.id, Client.status.ilike('schedule visit')).all()
    result = []
    for c in clients:
        reminder = Reminder.query.filter_by(client_id=c.id, employee_id=current_user.id, is_sent=False, message='Visit scheduled').order_by(Reminder.remind_at).first()
        visit_time = reminder.remind_at.strftime('%Y-%m-%d %H:%M') if reminder else ''
        result.append({
            'date': c.created_at.strftime('%Y-%m-%d') if c.created_at else '',
            'name': c.name,
            'phone': c.phone,
            'budget': c.budget,
            'area': c.area,
            'preferred_building': c.preferred_building,
            'status': c.status,
            'visit_time': visit_time
        })
    return jsonify(result)

@employee_bp.route('/clients/booked/json')
@login_required
def booked_clients_json():
    clients = Client.query.filter(Client.assigned_to==current_user.id, Client.status.ilike('booked')).all()
    return jsonify([{
        'date': c.created_at.strftime('%Y-%m-%d') if c.created_at else '',
        'name': c.name,
        'phone': c.phone,
        'budget': c.budget,
        'area': c.area,
        'preferred_building': c.preferred_building,
        'status': c.status
    } for c in clients])

@employee_bp.route('/reminders/upcoming/json')
@login_required
def upcoming_reminders_json():
    reminders = Reminder.query.filter_by(employee_id=current_user.id, is_sent=False).order_by(Reminder.remind_at).all()
    result = []
    for r in reminders:
        client = Client.query.get(r.client_id)
        result.append({
            'reminder_id': r.id,
            'date': r.remind_at.strftime('%Y-%m-%d'),
            'remind_at': r.remind_at.strftime('%Y-%m-%d %H:%M'),
            'message': r.message,
            'client_name': client.name if client else '',
            'client_id': r.client_id
        })
    return jsonify(result)

@employee_bp.route('/analytics/performance')
@login_required
def analytics_performance():
    import calendar
    from datetime import datetime
    year = datetime.now().year
    monthly_counts = [0] * 12
    clients = Client.query.filter_by(assigned_to=current_user.id).all()
    for c in clients:
        if c.created_at and c.created_at.year == year:
            monthly_counts[c.created_at.month - 1] += 1
    labels = [calendar.month_abbr[i+1] for i in range(12)]
    return jsonify({'labels': labels, 'values': monthly_counts})
 