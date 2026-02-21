
# 🚛 FleetFlow Lite

## Intelligent Fleet & Logistics Management Platform

FleetFlow Lite is a modular, role-based fleet and logistics management system designed to replace manual fleet logbooks with a centralized, rule-driven digital platform.

It provides structured dispatch workflows, compliance monitoring, maintenance tracking, and financial oversight within a controlled access environment.

---

# 🌐 Live Application

👉 **[Click Here !!!](https://odoo-x-gvp-hackathon.onrender.com/login)**
please logout first before starting !!!!

---

# 🎯 Problem Statement

Many small and mid-sized fleet operators rely on spreadsheets and disconnected logs to manage:

* Vehicle availability
* Driver compliance
* Trip assignments
* Maintenance tracking
* Fuel and operational costs

This results in:

* Lack of real-time visibility
* Dispatch errors
* Compliance risks
* Poor cost control

FleetFlow Lite solves this by introducing centralized role-based management, operational dashboards, and validation-driven workflows.

---

# 🔐 Role-Based Architecture

FleetFlow Lite enforces strict Role-Based Access Control (RBAC).

## Supported Roles

* **Fleet Manager**
* **Dispatcher**
* **Safety Officer**
* **Financial Analyst**

### Role Constraints

* Only **one active user per non-manager role**

  * Dispatcher
  * Safety Officer
  * Financial Analyst
* Manager account is pre-seeded (prototype mode)
* Non-manager roles require Manager approval
* Duplicate role assignment is restricted

This ensures structured organizational control.

---
---

# 👥 Role Responsibilities & Permissions

FleetFlow Lite operates on a structured single-company governance model where each role has clearly defined operational boundaries and responsibilities.

---

## 🟢 Fleet Manager (Administrative Control Layer)

The Fleet Manager is the central authority of the system and oversees overall fleet operations.

### Responsibilities:

- Approve or reject new role registration requests
- Remove existing role users (Dispatcher, Safety Officer, Financial Analyst)
- Add, update, and retire vehicles
- Log maintenance activities
- View complete fleet dashboard and operational metrics
- Maintain structural control of the organization

### System Privileges:

- Full access to all modules
- User approval and removal authority
- Cannot be self-registered (pre-seeded prototype account)

The Manager ensures governance, accountability, and system integrity.

---

## 🟡 Dispatcher (Operational Execution Layer)

The Dispatcher manages daily logistics and trip execution.

### Responsibilities:

- Create new trips
- Assign available vehicles and approved drivers
- Monitor and update trip lifecycle (Draft → Dispatched → Completed)
- Ensure operational readiness before dispatch

### System Constraints:

- Cannot approve users
- Cannot access financial analytics
- Cannot modify vehicle registry directly
- Cannot override compliance restrictions

The Dispatcher ensures cargo movement follows validated operational workflows.

---

## 🔵 Safety Officer (Compliance & Risk Control Layer)

The Safety Officer maintains driver compliance and regulatory safety standards.

### Responsibilities:

- Monitor driver license validity
- Update driver safety status
- Suspend or reactivate drivers
- Prevent assignment of non-compliant drivers

### System Constraints:

- Cannot dispatch trips
- Cannot modify financial records
- Cannot manage vehicle registry

The Safety Officer safeguards operational compliance and risk management.

---

## 🟣 Financial Analyst (Cost & Performance Monitoring Layer)

The Financial Analyst oversees cost tracking and financial transparency.

### Responsibilities:

- Record fuel logs
- Review maintenance expenses
- Monitor vehicle-level operational costs
- Analyze financial summaries from dashboard

### System Constraints:

- Cannot dispatch trips
- Cannot manage drivers
- Cannot approve user requests

The Financial Analyst ensures financial visibility and cost accountability.

---

## 🏢 Governance Model Summary

FleetFlow Lite enforces structured governance:

- One Fleet Manager (pre-seeded prototype)
- One Dispatcher
- One Safety Officer
- One Financial Analyst
- Registration requires Manager approval
- Duplicate role assignment is restricted

This design ensures:

✔ Clear separation of duties  
✔ Controlled system access  
✔ Operational accountability  
✔ Business-rule enforcement  

---

# 👤 Authentication & Approval Workflow

## Manager (Prototype Initialization)

On a fresh database, a default Manager account is automatically created for demonstration purposes:

* Username: `manager`
* Password: `manager123`

This account is intended for prototype demonstration during evaluation.

---

## Registration & Approval Process

1. User clicks **Request Access** on login page
2. Only unassigned roles appear in dropdown
3. User submits request
4. Account status is set to **Pending**
5. Manager reviews requests in dashboard
6. Manager can:

   * Approve → Access granted
   * Reject → Access permanently denied

Pending users cannot log in until approved.

---

# 🚗 Core Modules

## 1️⃣ Vehicle Registry

* Add and manage fleet vehicles
* Track load capacity, odometer, status
* Automated state transitions (Available / On Trip / In Shop)

---

## 2️⃣ Trip Dispatch & Validation

* Assign driver and vehicle
* Business rule enforcement:

  * Cargo ≤ Vehicle Capacity
  * Driver must be approved
  * Vehicle must not be in maintenance
* Trip lifecycle:

  * Draft → Dispatched → Completed

---

## 3️⃣ Driver Compliance (Safety Officer)

* Monitor license validity
* Update compliance status
* Suspend/reactivate drivers

---

## 4️⃣ Maintenance Management

* Log service events
* Automatically mark vehicle as “In Shop”
* Prevent dispatch during maintenance

---

## 5️⃣ Fuel & Financial Tracking

* Record fuel consumption
* Aggregate operational costs
* Provide cost-level visibility per vehicle

---

# 📊 Dashboard Capabilities

Manager Dashboard includes:

* Fleet status overview
* Role request management
* Operational cost summaries
* Trip metrics and tracking

Each role sees a restricted dashboard relevant to their responsibilities.

---

# 🛠 Technology Stack

| Layer             | Technology            |
| ----------------- | --------------------- |
| Backend           | Flask (Python)        |
| Frontend          | HTML, CSS, JavaScript |
| Database          | SQLite                |
| Production Server | Gunicorn              |
| Hosting           | Render                |

---

# 🧰 Local Setup Guide

## 1️⃣ Clone Repository

```bash
git clone https://github.com/mahipalsinghdeora/odoo_X_gvp_hackathon.git
cd odoo_X_gvp_hackathon
```

---

## 2️⃣ Install Dependencies

```bash
python -m pip install -r requirements.txt
```

---

## 3️⃣ Initialize Database (Optional Reset)

```bash
python init_db.py
```

This recreates database tables using `schema.sql`.

---

## 4️⃣ Run Application

```bash
python app.py
```

Open in browser:

```
http://127.0.0.1:5000/login
```

---

# 🚀 Production Deployment (Render)

Start command:

```bash
gunicorn -b 0.0.0.0:$PORT app:app
```

Set environment variable:

```
SECRET_KEY=<strong_random_key>
```

---

# 🔒 Security Features

* Session-based authentication
* Role-restricted routes
* Approval-controlled registration
* Business-rule enforcement
* SQLite foreign key integrity

---

# 📌 Project Scope

FleetFlow Lite was developed as a structured prototype for hackathon evaluation, demonstrating:

* Centralized fleet management
* Controlled access workflows
* Validation-driven dispatch
* Compliance monitoring
* Cost tracking capabilities

---

# 👥 Team

Developed for Hackathon Submission
FleetFlow Lite – 2026

---
