from . import db
from flask_login import UserMixin
from cryptography.fernet import Fernet
import bcrypt

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'employee'
    address = db.Column(db.String(255))
    aadhaar_number = db.Column(db.String(20))
    aadhaar_image = db.Column(db.String(255))  # Path to uploaded image
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(120))
    joining_date = db.Column(db.Date)
    leaving_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='approved')  # 'pending', 'approved', 'terminated'
    clients = db.relationship('Client', backref='employee', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    budget = db.Column(db.String(20))
    area = db.Column(db.String(120))
    preferred_building = db.Column(db.String(120))
    status = db.Column(db.String(50))  # e.g. 'visit scheduled', 'booked', 'paid'
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    type = db.Column(db.String(20))  # 'builder', 'broker', 'contractor'
    data = db.Column(db.String(255))  # Custom message

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    remind_at = db.Column(db.DateTime)
    message = db.Column(db.String(255))
    is_sent = db.Column(db.Boolean, default=False) 

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(80))
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)  # Optional JSON/text for extra info
    timestamp = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50))  # e.g. 'employee_registered', 'admin_pending'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Who triggered the notification
    status = db.Column(db.String(20), default='unread')  # 'unread', 'read'
    timestamp = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

def log_activity(user, action, details=None):
    from . import db  # local import to avoid circular import
    log = ActivityLog(
        user_id=user.id if user else None,
        username=user.username if user else None,
        action=action,
        details=details
    )
    db.session.add(log)
    db.session.commit() 