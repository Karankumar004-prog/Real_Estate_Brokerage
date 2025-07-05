from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from .utils import format_budget
import os
from flask_migrate import Migrate

# Initialize extensions
login_manager = LoginManager()
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()


def create_superadmin(app):
    from .models import User, db
    with app.app_context():
        if not User.query.filter_by(username='Admin1', role='admin').first():
            user = User(username='Admin1', role='admin', status='approved')
            user.set_password('aka123')
            db.session.add(user)
            db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, '../instance/real_estate.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'instance/aadhaar_uploads'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg'}

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    from .auth import auth_bp
    from .admin import admin_bp
    from .employee import employee_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)

    # Make format_budget available in Jinja templates
    app.jinja_env.globals['format_budget'] = format_budget

    @app.after_request
    def add_cache_control_headers(response):
        # Only set cache headers for protected routes
        if request.endpoint and (
            request.endpoint.startswith('admin.') or
            request.endpoint.startswith('employee.')
        ):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    # Call superadmin creation here
    create_superadmin(app)

    return app 