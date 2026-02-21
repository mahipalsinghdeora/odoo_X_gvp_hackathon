# 🚛 SmartFleet (FleetFlow Lite) – Intelligent Fleet & Logistics Management System

SmartFleet is a modular web-based fleet & logistics management system with role-based access, operational dashboards, and a lightweight decision-support workflow.

## 🌐 Live Demo

👉 **[Launch SmartFleet Application](https://odoo-x-gvp-hackathon.onrender.com/login)**

## 🚀 Core Features

### 🔐 Role-based access + approval workflow
- Roles: **Manager**, **Dispatcher**, **Safety Officer**, **Financial Analyst**
- Only **one user per non-manager role** (Dispatcher/Safety Officer/Financial Analyst)
- Self-registration is available for non-manager roles via **Request access**
- New registrations are created with status **pending** and must be **approved by the Manager** before login is allowed

### 🚗 Vehicle Registry
- Create and track vehicles (capacity, status, odometer)

### 📦 Trip Dispatcher
- Create trips and enforce basic validation (e.g., cargo weight)

### 🛠 Maintenance & ⛽ Fuel logs
- Track maintenance and fuel records

### 📊 Dashboards
- Manager dashboard includes fleet counts, cost rollups, and role-requests management

## 🛠 Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Flask (Python)
- Database: SQLite (file-based, stored as `fleetflow.db` in the project folder)
- Deployment: Render (supports `gunicorn`)

## 🧰 Local Setup

### 1) Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 2) Initialize/reset the database (optional)

```bash
python init_db.py
```

Note: `init_db.py` runs the schema in `schema.sql` (drops and recreates tables). Use it when you want a clean local database.

### 3) Run the app

```bash
python app.py
```

Then open: `http://127.0.0.1:5000/login`

## 🔑 Default Login (local)

On a fresh database, a Manager account is seeded automatically:

- Username: `manager`
- Password: `manager123`

## 🧾 Registration & Approval Flow

1. Go to `/register` (or click **Request access** on the login page)
2. Choose an available role (Dispatcher/Safety Officer/Financial Analyst)
3. Manager logs in → opens `/dashboard` → approves or rejects the request
4. Pending users cannot log in until approved

## ⚙️ Configuration

- `SECRET_KEY`: set a strong secret in production (defaults to a dev value)

Local runs (`python app.py`) use Flask defaults (host `127.0.0.1`, port `5000`). For hosting (e.g., Render), run with gunicorn and bind to the platform port, e.g.:

```bash
gunicorn -b 0.0.0.0:$PORT app:app
```

## 👥 Team

Developed for GVP Hackathon
