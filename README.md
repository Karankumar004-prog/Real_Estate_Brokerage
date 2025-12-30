# Real Estate Brokerage Management System

A comprehensive web application for managing real estate brokerage operations, including user (admin/employee) management, client tracking, partner management, analytics, and activity logging.

## Features

- **Admin Dashboard:**  
  - View analytics, employee/client/partner stats, and activity logs.
  - Manage employees, admins, and business partners.
  - Export data (CSV) for employees, admins, clients, partners, and activity logs.
  - Preview Aadhaar images for employees and admins.
  - **Admin1 is a super admin:** Cannot be deactivated, deleted, or edited by any other admin. Only Admin1 can edit their own details. Attempts to deactivate/delete Admin1 will show "Admin1 is super Admin".
  - **Notification system:** Only visible to Admin1.
  - **Real-time analytics and dashboard updates.**
  - **Comprehensive security:** All admin/employee actions are logged.
  - **Modern, responsive UI:** Built with Bootstrap 5 and Chart.js.

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
  - Conversion ratio, top employees/buildings, and monthly trends.
  - **Live updates:** All analytics and dashboard data update live when client or employee data changes.

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

### 4. Run the Application

```bash
python3 run.py
```

### 5. First Run & Login

- On first run, Admin1 is auto-created with password `aka123`.
- Go to `/login` (e.g., http://127.0.0.1:5000/login)
- You can register as admin or employee, or use:
  - **Admin:**
    - Username: `Admin1`
    - Password: `aka123`
- **Note:** 'Admin1' is a super admin. No one else can see the notification panel or change Admin1's password. Only Admin1 can edit their own details.

## Usage Notes

- **Aadhaar Image Uploads:**  
  Uploaded Aadhaar images are stored in `instance/aadhaar_uploads/` and are automatically renamed to the user's Aadhaar number (e.g., `123456789012.jpg`).
- **Preview Aadhaar Images:**  
  Use the "Preview" button in the Employees/Admins panels to view the Aadhaar image for any user.
- **Export Data:**  
  Use the export buttons in each panel to download CSVs of employees, admins, clients, partners, or activity logs.
- **Activity Logs:**  
  The admin dashboard provides a modal to view recent activity logs.
- **Admin1 Protection:**
  - Admin1 cannot be deactivated or deleted, even by Admin1. Attempts will show a message: "Admin1 is super Admin".
  - Only Admin1 can edit their own details. Other admins cannot edit Admin1.
  - Only Admin1 can approve new admin registrations.
- **Live Analytics:**
  - All analytics and dashboard data update live when client or employee data changes.

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
- **Admin1 is always protected:** Cannot be deactivated, deleted, or edited by anyone else.
- **Critical actions are blocked at both backend and frontend.**
- **Only Admin1 can approve new admin registrations.**
- **All actions are logged for auditing.**

## Production Readiness

- All features tested and verified.
- Ready for production deployment.
- Modern, responsive UI/UX.
- Real-time analytics and reporting.
- Comprehensive security and access control.

## License

**This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)**

---
