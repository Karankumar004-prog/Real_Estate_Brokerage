# Real Estate Brokerage Management System

A comprehensive web application for managing real estate brokerage operations, including user (admin/employee) management, client tracking, partner management, analytics, and activity logging.

## Features

- **Admin Dashboard:**  
  - View analytics, employee/client/partner stats, and activity logs.
  - Manage employees, admins, and business partners.
  - Export data (CSV) for employees, admins, clients, partners, and activity logs.
  - Preview Aadhaar images for employees and admins.

- **Employee Dashboard:**  
  - Manage assigned clients and view personal analytics.
  - Edit personal and client details.

- **User Management:**  
  - Registration and login for admins and employees.
  - Aadhaar number and image upload (images are renamed to the Aadhaar number for easy identification).
  - Account activation/deactivation, joining/leaving dates, and more.

- **Client & Partner Management:**  
  - Assign clients to employees, track client status, and preferred buildings.
  - Manage business partners (builders, brokers, contractors).

- **Activity Logging:**  
  - Track logins, edits, deletions, and other key actions.

- **Analytics:**  
  - Conversion ratio, revenue, top employees/buildings, and monthly trends.

## Project Structure

```
Real_Estate_Brokerage/
│
├── app/
│   ├── __init__.py
│   ├── admin.py
│   ├── auth.py
│   ├── employee.py
│   ├── models.py
│   ├── utils.py
│   └── templates/
│       ├── admin/
│       │   ├── dashboard.html
│       │   └── activity_logs.html
│       ├── employee/
│       │   ├── dashboard.html
│       │   └── clients.html
│       ├── register.html
│       ├── login.html
│       └── unauthorized.html
│
├── instance/
│   └── aadhaar_uploads/   # Stores uploaded Aadhaar images, named as <aadhaar_number>.jpg/png
│
├── migrations/            # Flask-Migrate database migrations
│
├── requirements.txt
├── run.py
└── README.md
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Real_Estate_Brokerage
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize the Database

```bash
flask db init
flask db migrate
flask db upgrade
```

> The SQLite database will be created at `instance/real_estate.db`.

### 5. Run the Application

```bash
python run.py
```

The app will be available at [http://127.0.0.1:5000] or (https://127.0.0.1:5000).

## Usage Notes

- **Aadhaar Image Uploads:**  
  Uploaded Aadhaar images are stored in `instance/aadhaar_uploads/` and are automatically renamed to the user's Aadhaar number (e.g., `123456789012.jpg`).
- **Preview Aadhaar Images:**  
  Use the "Preview" button in the Employees/Admins panels to view the Aadhaar image for any user.
- **Export Data:**  
  Use the export buttons in each panel to download CSVs of employees, admins, clients, partners, or activity logs.
- **Activity Logs:**  
  The admin dashboard provides a modal to view recent activity logs.

## Main Models

- **User:** Admins and employees, with fields for contact info, Aadhaar, status, etc.
- **Client:** Real estate clients, assigned to employees.
- **Partner:** Business partners (builders, brokers, contractors).
- **ActivityLog:** Tracks user actions for auditing.
- **Reminder:** (Optional) For client follow-ups.

## Requirements

See `requirements.txt`:
```
Flask
Flask-Login
Flask-SQLAlchemy
bcrypt
cryptography
pandas
Flask-Mail
```

## Migrations

Uses Flask-Migrate.  
If you change models, run:
```bash
flask db migrate
flask db upgrade
```

## Security

- Passwords are hashed with bcrypt.
- Session management via Flask-Login.
- Admin/employee access control on all routes.

## License

[MIT License] (or your preferred license)

---

Let me know if you want to add screenshots, deployment instructions, or any other custom sections! 