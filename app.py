from datetime import date, datetime
from functools import wraps
from pathlib import Path
import os
import sqlite3

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "fleetflow.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fleetflow-lite-dev-secret")

ASSIGNABLE_ROLES = ["Dispatcher", "Safety Officer", "Financial Analyst"]
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


# ------------------------
# Database helpers
# ------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    schema_path = BASE_DIR / "schema.sql"
    with get_db_connection() as conn:
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            conn.executescript(schema_file.read())
        conn.commit()


def seed_default_users():
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (username, password_hash, role, status)
            VALUES (?, ?, 'Manager', ?)
            """,
            ("manager", generate_password_hash("manager123"), STATUS_APPROVED),
        )
        conn.commit()


def is_license_expired(expiry_date_text):
    if not expiry_date_text:
        return True
    return datetime.strptime(expiry_date_text, "%Y-%m-%d").date() < date.today()


def get_role_home_endpoint(role):
    home_by_role = {
        "Manager": "dashboard",
        "Dispatcher": "trips",
        "Safety Officer": "safety_dashboard",
        "Financial Analyst": "financial_dashboard",
    }
    return home_by_role.get(role, "login")


def ensure_schema_updates():
    with get_db_connection() as conn:
        users_table_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        users_table_sql_text = users_table_sql["sql"] if users_table_sql else ""

        if "Safety Officer" not in users_table_sql_text or "Financial Analyst" not in users_table_sql_text:
            conn.execute("ALTER TABLE users RENAME TO users_old")
            conn.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    name TEXT,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('Manager', 'Dispatcher', 'Safety Officer', 'Financial Analyst')),
                    status TEXT NOT NULL DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'rejected'))
                )
                """
            )
            conn.execute(
                """
                INSERT INTO users (id, username, password_hash, role)
                SELECT id, username, password_hash, role FROM users_old
                """
            )
            conn.execute("DROP TABLE users_old")

        users_columns = {
            column_info["name"]
            for column_info in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "name" not in users_columns:
            conn.execute("ALTER TABLE users ADD COLUMN name TEXT")
        if "email" not in users_columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "status" not in users_columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'approved'"
            )

        conn.execute(
            "UPDATE users SET status = 'approved' WHERE status IS NULL OR TRIM(status) = ''"
        )

        driver_columns = {
            column_info["name"]
            for column_info in conn.execute("PRAGMA table_info(drivers)").fetchall()
        }
        if "safety_score" not in driver_columns:
            conn.execute(
                "ALTER TABLE drivers ADD COLUMN safety_score INTEGER NOT NULL DEFAULT 75"
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fuel_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                liters REAL NOT NULL CHECK (liters > 0),
                cost REAL NOT NULL CHECK (cost >= 0),
                date TEXT NOT NULL,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT
            )
            """
        )
        conn.commit()


def get_available_roles_for_registration(conn):
    taken = {
        row["role"]
        for row in conn.execute(
            """
            SELECT role
            FROM users
            WHERE role IN ('Dispatcher', 'Safety Officer', 'Financial Analyst')
              AND status IN ('pending', 'approved')
            """
        ).fetchall()
    }
    return [role for role in ASSIGNABLE_ROLES if role not in taken]


# ------------------------
# Auth / access
# ------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def roles_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in allowed_roles:
                flash("You do not have permission to access this action.", "error")
                return redirect(url_for(get_role_home_endpoint(session.get("role"))))
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


@app.before_request
def load_current_user():
    g.user = None
    user_id = session.get("user_id")
    if not user_id:
        return

    with get_db_connection() as conn:
        g.user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# ------------------------
# Routes
# ------------------------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for(get_role_home_endpoint(session.get("role"))))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db_connection() as conn:
            user = conn.execute(
                """
                SELECT *
                FROM users
                WHERE lower(username) = lower(?) OR lower(email) = lower(?)
                """,
                (username, username),
            ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        status = user["status"] if ("status" in user.keys()) else STATUS_APPROVED
        if status == STATUS_PENDING:
            flash("Awaiting manager approval", "error")
            return render_template("login.html")
        if status == STATUS_REJECTED:
            flash("Access denied by manager", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        flash("Logged in successfully.", "success")
        return redirect(url_for(get_role_home_endpoint(user["role"])))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    with get_db_connection() as conn:
        available_roles = get_available_roles_for_registration(conn)
        all_roles_assigned = len(available_roles) == 0

        if request.method == "POST":
            if all_roles_assigned:
                flash("All roles assigned", "error")
                return render_template(
                    "register.html",
                    available_roles=available_roles,
                    all_roles_assigned=all_roles_assigned,
                )

            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            role = request.form.get("role", "").strip()

            if not all([name, email, password, role]):
                flash("All fields are required", "error")
                return render_template(
                    "register.html",
                    available_roles=available_roles,
                    all_roles_assigned=all_roles_assigned,
                )

            if role not in available_roles:
                flash("Selected role is not available", "error")
                return render_template(
                    "register.html",
                    available_roles=available_roles,
                    all_roles_assigned=all_roles_assigned,
                )

            # Store email as username to avoid changing the login UI/field
            try:
                conn.execute(
                    """
                    INSERT INTO users (username, name, email, password_hash, role, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email,
                        name,
                        email,
                        generate_password_hash(password),
                        role,
                        STATUS_PENDING,
                    ),
                )
                conn.commit()
                flash("Request submitted", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                conn.rollback()
                flash("Email already registered", "error")
                return render_template(
                    "register.html",
                    available_roles=get_available_roles_for_registration(conn),
                    all_roles_assigned=(len(get_available_roles_for_registration(conn)) == 0),
                )

        return render_template(
            "register.html",
            available_roles=available_roles,
            all_roles_assigned=all_roles_assigned,
        )


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@roles_required("Manager")
def dashboard():
    with get_db_connection() as conn:
        active_fleet = conn.execute(
            "SELECT COUNT(*) FROM vehicles WHERE status = 'On Trip'"
        ).fetchone()[0]
        in_maintenance = conn.execute(
            "SELECT COUNT(*) FROM vehicles WHERE status = 'In Shop'"
        ).fetchone()[0]
        available_vehicles = conn.execute(
            "SELECT COUNT(*) FROM vehicles WHERE status = 'Available'"
        ).fetchone()[0]
        pending_trips = conn.execute(
            "SELECT COUNT(*) FROM trips WHERE status = 'Draft'"
        ).fetchone()[0]
        expired_licenses = conn.execute(
            "SELECT COUNT(*) FROM drivers WHERE date(license_expiry_date) < date('now')"
        ).fetchone()[0]
        avg_safety_score = conn.execute(
            "SELECT ROUND(COALESCE(AVG(safety_score), 0), 2) FROM drivers"
        ).fetchone()[0]
        total_operational_cost = conn.execute(
            """
            SELECT
                COALESCE((SELECT SUM(cost) FROM maintenance_logs), 0)
                + COALESCE((SELECT SUM(cost) FROM fuel_logs), 0)
            """
        ).fetchone()[0]
        recent_trips = conn.execute(
            """
            SELECT t.id, t.origin, t.destination, t.status,
                   v.license_plate, d.name AS driver_name
            FROM trips t
            JOIN vehicles v ON t.vehicle_id = v.id
            JOIN drivers d ON t.driver_id = d.id
            ORDER BY t.id DESC
            LIMIT 8
            """
        ).fetchall()

        pending_role_requests = conn.execute(
            """
            SELECT id, name, email, role
            FROM users
            WHERE status = 'pending' AND role != 'Manager'
            ORDER BY id DESC
            """
        ).fetchall()

        approved_role_users = conn.execute(
            """
            SELECT id, name, email, role
            FROM users
            WHERE status = 'approved' AND role IN ('Dispatcher', 'Safety Officer', 'Financial Analyst')
            ORDER BY role
            """
        ).fetchall()

    return render_template(
        "manager_dashboard.html",
        active_fleet=active_fleet,
        in_maintenance=in_maintenance,
        available_vehicles=available_vehicles,
        pending_trips=pending_trips,
        expired_licenses=expired_licenses,
        avg_safety_score=avg_safety_score,
        total_operational_cost=total_operational_cost,
        recent_trips=recent_trips,
        pending_role_requests=pending_role_requests,
        approved_role_users=approved_role_users,
    )


@app.route("/users/<int:user_id>/approve", methods=["POST"])
@roles_required("Manager")
def approve_user(user_id):
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            flash("Request not found", "error")
            return redirect(url_for("dashboard"))
        if user["role"] == "Manager":
            flash("Cannot approve manager role", "error")
            return redirect(url_for("dashboard"))
        if user["status"] != STATUS_PENDING:
            flash("Request is not pending", "error")
            return redirect(url_for("dashboard"))

        # Only one user per role (treat pending+approved as occupying the role)
        conflict = conn.execute(
            """
            SELECT 1 FROM users
            WHERE role = ? AND status IN ('pending', 'approved') AND id != ?
            LIMIT 1
            """,
            (user["role"], user_id),
        ).fetchone()
        if conflict:
            flash("Role already assigned", "error")
            return redirect(url_for("dashboard"))

        conn.execute("UPDATE users SET status = ? WHERE id = ?", (STATUS_APPROVED, user_id))
        conn.commit()
        flash("User approved", "success")
        return redirect(url_for("dashboard"))


@app.route("/users/<int:user_id>/reject", methods=["POST"])
@roles_required("Manager")
def reject_user(user_id):
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            flash("Request not found", "error")
            return redirect(url_for("dashboard"))
        if user["role"] == "Manager":
            flash("Cannot reject manager role", "error")
            return redirect(url_for("dashboard"))
        if user["status"] != STATUS_PENDING:
            flash("Request is not pending", "error")
            return redirect(url_for("dashboard"))

        conn.execute("UPDATE users SET status = ? WHERE id = ?", (STATUS_REJECTED, user_id))
        conn.commit()
        flash("User rejected", "success")
        return redirect(url_for("dashboard"))


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@roles_required("Manager")
def delete_user(user_id):
    if session.get("user_id") == user_id:
        flash("Manager cannot delete self", "error")
        return redirect(url_for("dashboard"))

    with get_db_connection() as conn:
        user = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            flash("User not found", "error")
            return redirect(url_for("dashboard"))
        if user["role"] == "Manager":
            flash("Manager cannot be removed", "error")
            return redirect(url_for("dashboard"))

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash("User removed", "success")
        return redirect(url_for("dashboard"))


@app.route("/vehicles", methods=["GET", "POST"])
@roles_required("Manager")
def vehicles():
    if request.method == "POST":
        if session.get("role") != "Manager":
            flash("Only managers can create vehicles.", "error")
            return redirect(url_for("vehicles"))

        model_name = request.form.get("model_name", "").strip()
        license_plate = request.form.get("license_plate", "").strip().upper()
        max_capacity_kg = request.form.get("max_capacity_kg", type=float)
        odometer = request.form.get("odometer", type=int)
        status = request.form.get("status", "Available").strip()

        if not model_name or not license_plate:
            flash("Model name and license plate are required.", "error")
            return redirect(url_for("vehicles"))
        if max_capacity_kg is None or max_capacity_kg <= 0:
            flash("Max capacity must be a positive number.", "error")
            return redirect(url_for("vehicles"))
        if odometer is None or odometer < 0:
            flash("Odometer must be zero or greater.", "error")
            return redirect(url_for("vehicles"))
        if status not in {"Available", "On Trip", "In Shop"}:
            flash("Invalid vehicle status.", "error")
            return redirect(url_for("vehicles"))

        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO vehicles (model_name, license_plate, max_capacity_kg, odometer, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (model_name, license_plate, max_capacity_kg, odometer, status),
                )
                conn.commit()
            flash("Vehicle created.", "success")
        except sqlite3.IntegrityError:
            flash("License plate must be unique.", "error")

        return redirect(url_for("vehicles"))

    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM vehicles ORDER BY id DESC"
        ).fetchall()
    return render_template("vehicles.html", vehicles=rows)


@app.route("/vehicles/<int:vehicle_id>/edit", methods=["GET", "POST"])
@roles_required("Manager")
def edit_vehicle(vehicle_id):
    with get_db_connection() as conn:
        vehicle = conn.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
        if not vehicle:
            flash("Vehicle not found.", "error")
            return redirect(url_for("vehicles"))

        if request.method == "POST":
            model_name = request.form.get("model_name", "").strip()
            license_plate = request.form.get("license_plate", "").strip().upper()
            max_capacity_kg = request.form.get("max_capacity_kg", type=float)
            odometer = request.form.get("odometer", type=int)
            status = request.form.get("status", "Available").strip()

            if not model_name or not license_plate:
                flash("Model name and license plate are required.", "error")
                return redirect(url_for("edit_vehicle", vehicle_id=vehicle_id))
            if max_capacity_kg is None or max_capacity_kg <= 0:
                flash("Max capacity must be a positive number.", "error")
                return redirect(url_for("edit_vehicle", vehicle_id=vehicle_id))
            if odometer is None or odometer < 0:
                flash("Odometer must be zero or greater.", "error")
                return redirect(url_for("edit_vehicle", vehicle_id=vehicle_id))
            if status not in {"Available", "On Trip", "In Shop"}:
                flash("Invalid vehicle status.", "error")
                return redirect(url_for("edit_vehicle", vehicle_id=vehicle_id))

            try:
                conn.execute(
                    """
                    UPDATE vehicles
                    SET model_name = ?, license_plate = ?, max_capacity_kg = ?, odometer = ?, status = ?
                    WHERE id = ?
                    """,
                    (model_name, license_plate, max_capacity_kg, odometer, status, vehicle_id),
                )
                conn.commit()
                flash("Vehicle updated.", "success")
                return redirect(url_for("vehicles"))
            except sqlite3.IntegrityError:
                flash("License plate must be unique.", "error")
                return redirect(url_for("edit_vehicle", vehicle_id=vehicle_id))

    return render_template("vehicle_edit.html", vehicle=vehicle)


@app.route("/vehicles/<int:vehicle_id>/delete", methods=["POST"])
@roles_required("Manager")
def delete_vehicle(vehicle_id):
    with get_db_connection() as conn:
        in_use = conn.execute(
            "SELECT 1 FROM trips WHERE vehicle_id = ? LIMIT 1", (vehicle_id,)
        ).fetchone()
        if in_use:
            flash("Vehicle cannot be deleted because it has trip records.", "error")
            return redirect(url_for("vehicles"))

        conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        conn.commit()
    flash("Vehicle deleted.", "success")
    return redirect(url_for("vehicles"))


@app.route("/drivers", methods=["GET", "POST"])
@roles_required("Manager", "Dispatcher", "Safety Officer", "Financial Analyst")
def drivers():
    if request.method == "POST":
        if session.get("role") != "Manager":
            flash("Only managers can create drivers.", "error")
            return redirect(url_for("drivers"))

        name = request.form.get("name", "").strip()
        license_number = request.form.get("license_number", "").strip().upper()
        license_expiry_date = request.form.get("license_expiry_date", "").strip()
        status = request.form.get("status", "Available").strip()

        if not all([name, license_number, license_expiry_date]):
            flash("All driver fields are required.", "error")
            return redirect(url_for("drivers"))
        if status not in {"Available", "On Trip", "Suspended"}:
            flash("Invalid driver status.", "error")
            return redirect(url_for("drivers"))

        try:
            datetime.strptime(license_expiry_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid license expiry date.", "error")
            return redirect(url_for("drivers"))

        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO drivers (name, license_number, license_expiry_date, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, license_number, license_expiry_date, status),
                )
                conn.commit()
            flash("Driver created.", "success")
        except sqlite3.IntegrityError:
            flash("License number must be unique.", "error")

        return redirect(url_for("drivers"))

    with get_db_connection() as conn:
        if session.get("role") == "Dispatcher":
            rows = conn.execute(
                """
                SELECT *
                FROM drivers
                WHERE status = 'Available' AND date(license_expiry_date) >= date('now')
                ORDER BY id DESC
                """
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM drivers ORDER BY id DESC").fetchall()
    return render_template("drivers.html", drivers=rows)


@app.route("/drivers/<int:driver_id>/edit", methods=["GET", "POST"])
@roles_required("Manager")
def edit_driver(driver_id):
    with get_db_connection() as conn:
        driver = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
        if not driver:
            flash("Driver not found.", "error")
            return redirect(url_for("drivers"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            license_number = request.form.get("license_number", "").strip().upper()
            license_expiry_date = request.form.get("license_expiry_date", "").strip()
            status = request.form.get("status", "Available").strip()

            if not all([name, license_number, license_expiry_date]):
                flash("All driver fields are required.", "error")
                return redirect(url_for("edit_driver", driver_id=driver_id))
            if status not in {"Available", "On Trip", "Suspended"}:
                flash("Invalid driver status.", "error")
                return redirect(url_for("edit_driver", driver_id=driver_id))
            try:
                datetime.strptime(license_expiry_date, "%Y-%m-%d")
            except ValueError:
                flash("Invalid license expiry date.", "error")
                return redirect(url_for("edit_driver", driver_id=driver_id))

            try:
                conn.execute(
                    """
                    UPDATE drivers
                    SET name = ?, license_number = ?, license_expiry_date = ?, status = ?
                    WHERE id = ?
                    """,
                    (name, license_number, license_expiry_date, status, driver_id),
                )
                conn.commit()
                flash("Driver updated.", "success")
                return redirect(url_for("drivers"))
            except sqlite3.IntegrityError:
                flash("License number must be unique.", "error")
                return redirect(url_for("edit_driver", driver_id=driver_id))

    return render_template("driver_edit.html", driver=driver)


@app.route("/drivers/<int:driver_id>/delete", methods=["POST"])
@roles_required("Manager")
def delete_driver(driver_id):
    with get_db_connection() as conn:
        in_use = conn.execute(
            "SELECT 1 FROM trips WHERE driver_id = ? LIMIT 1", (driver_id,)
        ).fetchone()
        if in_use:
            flash("Driver cannot be deleted because they have trip records.", "error")
            return redirect(url_for("drivers"))

        conn.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))
        conn.commit()
    flash("Driver deleted.", "success")
    return redirect(url_for("drivers"))


def validate_trip_assignment(conn, vehicle_id, driver_id, cargo_weight, status, old_status=None):
    vehicle = conn.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
    driver = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()

    if not vehicle or not driver:
        return "Vehicle or driver not found.", None, None

    if cargo_weight is None or cargo_weight <= 0:
        return "Cargo weight must be a positive number.", None, None

    if cargo_weight > vehicle["max_capacity_kg"]:
        return "Cargo weight exceeds vehicle maximum capacity.", None, None

    if vehicle["status"] == "In Shop":
        return "Vehicle in shop cannot be assigned to trip.", None, None

    if is_license_expired(driver["license_expiry_date"]):
        return "Driver license is expired and cannot be assigned.", None, None

    if driver["status"] != "Available" and old_status != "Dispatched":
        return "Driver is not available for assignment.", None, None

    if status == "Dispatched":
        if vehicle["status"] != "Available" and old_status != "Dispatched":
            return "Vehicle must be available to dispatch.", None, None
        if driver["status"] != "Available" and old_status != "Dispatched":
            return "Driver must be available to dispatch.", None, None

    return None, vehicle, driver


@app.route("/trips", methods=["GET", "POST"])
@roles_required("Dispatcher")
def trips():
    if request.method == "POST":
        vehicle_id = request.form.get("vehicle_id", type=int)
        driver_id = request.form.get("driver_id", type=int)
        cargo_weight = request.form.get("cargo_weight", type=float)
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()
        status = request.form.get("status", "Draft").strip()

        if status not in {"Draft", "Dispatched", "Completed", "Cancelled"}:
            flash("Invalid trip status.", "error")
            return redirect(url_for("trips"))
        if not all([vehicle_id, driver_id, origin, destination]):
            flash("All trip fields are required.", "error")
            return redirect(url_for("trips"))

        with get_db_connection() as conn:
            error, _, _ = validate_trip_assignment(
                conn, vehicle_id, driver_id, cargo_weight, status
            )
            if error:
                flash(error, "error")
                return redirect(url_for("trips"))

            conn.execute(
                """
                INSERT INTO trips (vehicle_id, driver_id, cargo_weight, origin, destination, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (vehicle_id, driver_id, cargo_weight, origin, destination, status),
            )

            if status == "Dispatched":
                conn.execute(
                    "UPDATE vehicles SET status = 'On Trip' WHERE id = ?", (vehicle_id,)
                )
                conn.execute(
                    "UPDATE drivers SET status = 'On Trip' WHERE id = ?", (driver_id,)
                )
            elif status in {"Completed", "Cancelled"}:
                conn.execute(
                    "UPDATE vehicles SET status = 'Available' WHERE id = ?", (vehicle_id,)
                )
                conn.execute(
                    "UPDATE drivers SET status = 'Available' WHERE id = ?", (driver_id,)
                )

            conn.commit()

        flash("Trip created.", "success")
        return redirect(url_for("trips"))

    with get_db_connection() as conn:
        trip_rows = conn.execute(
            """
            SELECT t.*, v.license_plate, d.name AS driver_name
            FROM trips t
            JOIN vehicles v ON t.vehicle_id = v.id
            JOIN drivers d ON t.driver_id = d.id
            ORDER BY t.id DESC
            """
        ).fetchall()
        vehicle_rows = conn.execute(
            "SELECT * FROM vehicles WHERE status != 'In Shop' ORDER BY license_plate"
        ).fetchall()
        driver_rows = conn.execute(
            """
            SELECT *
            FROM drivers
            WHERE status = 'Available' AND date(license_expiry_date) >= date('now')
            ORDER BY name
            """
        ).fetchall()

    return render_template(
        "trips.html",
        trips=trip_rows,
        vehicles=vehicle_rows,
        drivers=driver_rows,
    )


@app.route("/trips/<int:trip_id>/status", methods=["POST"])
@roles_required("Dispatcher")
def update_trip_status(trip_id):
    new_status = request.form.get("status", "").strip()
    if new_status not in {"Draft", "Dispatched", "Completed", "Cancelled"}:
        flash("Invalid trip status.", "error")
        return redirect(url_for("trips"))

    with get_db_connection() as conn:
        trip = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if not trip:
            flash("Trip not found.", "error")
            return redirect(url_for("trips"))

        old_status = trip["status"]
        if old_status == new_status:
            flash("Trip status unchanged.", "success")
            return redirect(url_for("trips"))

        error, _, _ = validate_trip_assignment(
            conn,
            trip["vehicle_id"],
            trip["driver_id"],
            trip["cargo_weight"],
            new_status,
            old_status=old_status,
        )
        if error:
            flash(error, "error")
            return redirect(url_for("trips"))

        conn.execute("UPDATE trips SET status = ? WHERE id = ?", (new_status, trip_id))

        if new_status == "Dispatched":
            conn.execute(
                "UPDATE vehicles SET status = 'On Trip' WHERE id = ?", (trip["vehicle_id"],)
            )
            conn.execute(
                "UPDATE drivers SET status = 'On Trip' WHERE id = ?", (trip["driver_id"],)
            )
        elif new_status in {"Completed", "Cancelled", "Draft"}:
            conn.execute(
                "UPDATE vehicles SET status = 'Available' WHERE id = ?", (trip["vehicle_id"],)
            )
            conn.execute(
                "UPDATE drivers SET status = 'Available' WHERE id = ?", (trip["driver_id"],)
            )

        conn.commit()

    flash("Trip status updated.", "success")
    return redirect(url_for("trips"))


@app.route("/trips/<int:trip_id>/delete", methods=["POST"])
@roles_required("Dispatcher")
def delete_trip(trip_id):
    flash("Trip deletion is disabled by current role policy.", "error")
    return redirect(url_for("trips"))


@app.route("/maintenance", methods=["GET", "POST"])
@roles_required("Manager")
def maintenance():
    if request.method == "POST":
        vehicle_id = request.form.get("vehicle_id", type=int)
        description = request.form.get("description", "").strip()
        cost = request.form.get("cost", type=float)
        log_date = request.form.get("date", "").strip()

        if not all([vehicle_id, description, log_date]):
            flash("All maintenance fields are required.", "error")
            return redirect(url_for("maintenance"))
        if cost is None or cost < 0:
            flash("Cost must be zero or greater.", "error")
            return redirect(url_for("maintenance"))

        try:
            datetime.strptime(log_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid maintenance date.", "error")
            return redirect(url_for("maintenance"))

        with get_db_connection() as conn:
            vehicle = conn.execute(
                "SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)
            ).fetchone()
            if not vehicle:
                flash("Vehicle not found.", "error")
                return redirect(url_for("maintenance"))

            conn.execute(
                """
                INSERT INTO maintenance_logs (vehicle_id, description, cost, date)
                VALUES (?, ?, ?, ?)
                """,
                (vehicle_id, description, cost, log_date),
            )
            conn.execute(
                "UPDATE vehicles SET status = 'In Shop' WHERE id = ?", (vehicle_id,)
            )
            conn.commit()

        flash("Maintenance log created. Vehicle moved to In Shop.", "success")
        return redirect(url_for("maintenance"))

    with get_db_connection() as conn:
        vehicle_rows = conn.execute(
            "SELECT * FROM vehicles ORDER BY license_plate"
        ).fetchall()
        logs = conn.execute(
            """
            SELECT m.*, v.license_plate
            FROM maintenance_logs m
            JOIN vehicles v ON m.vehicle_id = v.id
            ORDER BY m.id DESC
            """
        ).fetchall()

    return render_template("maintenance.html", vehicles=vehicle_rows, logs=logs)


@app.route("/safety/dashboard")
@roles_required("Safety Officer")
def safety_dashboard():
    with get_db_connection() as conn:
        expired_licenses = conn.execute(
            "SELECT COUNT(*) FROM drivers WHERE date(license_expiry_date) < date('now')"
        ).fetchone()[0]
        suspended_drivers = conn.execute(
            "SELECT COUNT(*) FROM drivers WHERE status = 'Suspended'"
        ).fetchone()[0]
        avg_safety_score = conn.execute(
            "SELECT ROUND(COALESCE(AVG(safety_score), 0), 2) FROM drivers"
        ).fetchone()[0]

    return render_template(
        "safety_dashboard.html",
        expired_licenses=expired_licenses,
        suspended_drivers=suspended_drivers,
        avg_safety_score=avg_safety_score,
    )


@app.route("/safety/drivers")
@roles_required("Safety Officer")
def safety_drivers():
    with get_db_connection() as conn:
        drivers_with_metrics = conn.execute(
            """
            SELECT
                d.*,
                CASE WHEN date(d.license_expiry_date) < date('now') THEN 1 ELSE 0 END AS is_expired,
                COALESCE(SUM(CASE WHEN t.status = 'Completed' THEN 1 ELSE 0 END), 0) AS completed_trip_count
            FROM drivers d
            LEFT JOIN trips t ON t.driver_id = d.id
            GROUP BY d.id
            ORDER BY d.name
            """
        ).fetchall()

    return render_template("driver_compliance.html", drivers=drivers_with_metrics)


@app.route("/safety/drivers/<int:driver_id>/update", methods=["POST"])
@roles_required("Safety Officer")
def safety_update_driver(driver_id):
    safety_score = request.form.get("safety_score", type=int)
    status = request.form.get("status", "").strip()

    if safety_score is None or safety_score < 0 or safety_score > 100:
        flash("Safety score must be between 0 and 100.", "error")
        return redirect(url_for("safety_drivers"))
    if status not in {"Available", "Suspended"}:
        flash("Status must be Available or Suspended.", "error")
        return redirect(url_for("safety_drivers"))

    with get_db_connection() as conn:
        driver = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
        if not driver:
            flash("Driver not found.", "error")
            return redirect(url_for("safety_drivers"))

        if driver["status"] == "On Trip" and status == "Suspended":
            flash("Cannot suspend a driver currently on trip.", "error")
            return redirect(url_for("safety_drivers"))

        conn.execute(
            "UPDATE drivers SET safety_score = ?, status = ? WHERE id = ?",
            (safety_score, status, driver_id),
        )
        conn.commit()

    flash("Driver compliance profile updated.", "success")
    return redirect(url_for("safety_drivers"))


@app.route("/financial/dashboard", methods=["GET", "POST"])
@roles_required("Financial Analyst")
def financial_dashboard():
    if request.method == "POST":
        vehicle_id = request.form.get("vehicle_id", type=int)
        liters = request.form.get("liters", type=float)
        cost = request.form.get("cost", type=float)
        log_date = request.form.get("date", "").strip()

        if not vehicle_id or liters is None or cost is None or not log_date:
            flash("All fuel log fields are required.", "error")
            return redirect(url_for("financial_dashboard"))
        if liters <= 0:
            flash("Fuel liters must be greater than zero.", "error")
            return redirect(url_for("financial_dashboard"))
        if cost < 0:
            flash("Fuel cost must be zero or greater.", "error")
            return redirect(url_for("financial_dashboard"))

        try:
            datetime.strptime(log_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid fuel log date.", "error")
            return redirect(url_for("financial_dashboard"))

        with get_db_connection() as conn:
            vehicle = conn.execute(
                "SELECT id FROM vehicles WHERE id = ?", (vehicle_id,)
            ).fetchone()
            if not vehicle:
                flash("Vehicle not found.", "error")
                return redirect(url_for("financial_dashboard"))

            conn.execute(
                """
                INSERT INTO fuel_logs (vehicle_id, liters, cost, date)
                VALUES (?, ?, ?, ?)
                """,
                (vehicle_id, liters, cost, log_date),
            )
            conn.commit()

        flash("Fuel log added.", "success")
        return redirect(url_for("financial_dashboard"))

    with get_db_connection() as conn:
        total_fuel_cost = conn.execute(
            "SELECT ROUND(COALESCE(SUM(cost), 0), 2) FROM fuel_logs"
        ).fetchone()[0]
        total_maintenance_cost = conn.execute(
            "SELECT ROUND(COALESCE(SUM(cost), 0), 2) FROM maintenance_logs"
        ).fetchone()[0]
        total_operational_cost = round(total_fuel_cost + total_maintenance_cost, 2)

        completed_trip_count = conn.execute(
            "SELECT COUNT(*) FROM trips WHERE status = 'Completed'"
        ).fetchone()[0]

        cost_rows = conn.execute(
            """
            SELECT
                v.id,
                v.license_plate,
                v.model_name,
                ROUND(COALESCE(f.total_fuel_cost, 0), 2) AS total_fuel_cost,
                ROUND(COALESCE(m.total_maintenance_cost, 0), 2) AS total_maintenance_cost,
                ROUND(COALESCE(f.total_fuel_cost, 0) + COALESCE(m.total_maintenance_cost, 0), 2) AS total_operational_cost,
                COALESCE(tc.completed_trips, 0) AS completed_trips,
                CASE
                    WHEN COALESCE(tc.completed_trips, 0) = 0 THEN NULL
                    ELSE ROUND((COALESCE(f.total_fuel_cost, 0) + COALESCE(m.total_maintenance_cost, 0)) / tc.completed_trips, 2)
                END AS cost_per_trip
            FROM vehicles v
            LEFT JOIN (
                SELECT vehicle_id, SUM(cost) AS total_fuel_cost
                FROM fuel_logs
                GROUP BY vehicle_id
            ) f ON f.vehicle_id = v.id
            LEFT JOIN (
                SELECT vehicle_id, SUM(cost) AS total_maintenance_cost
                FROM maintenance_logs
                GROUP BY vehicle_id
            ) m ON m.vehicle_id = v.id
            LEFT JOIN (
                SELECT vehicle_id, COUNT(*) AS completed_trips
                FROM trips
                WHERE status = 'Completed'
                GROUP BY vehicle_id
            ) tc ON tc.vehicle_id = v.id
            ORDER BY v.license_plate
            """
        ).fetchall()

        completed_trips = conn.execute(
            """
            SELECT t.id, t.origin, t.destination, t.cargo_weight, v.license_plate, d.name AS driver_name
            FROM trips t
            JOIN vehicles v ON v.id = t.vehicle_id
            JOIN drivers d ON d.id = t.driver_id
            WHERE t.status = 'Completed'
            ORDER BY t.id DESC
            LIMIT 10
            """
        ).fetchall()

        maintenance_recent = conn.execute(
            """
            SELECT m.id, m.description, m.cost, m.date, v.license_plate
            FROM maintenance_logs m
            JOIN vehicles v ON v.id = m.vehicle_id
            ORDER BY m.id DESC
            LIMIT 10
            """
        ).fetchall()

        vehicles = conn.execute("SELECT id, license_plate FROM vehicles ORDER BY license_plate").fetchall()

    return render_template(
        "financial_dashboard.html",
        total_fuel_cost=total_fuel_cost,
        total_maintenance_cost=total_maintenance_cost,
        total_operational_cost=total_operational_cost,
        completed_trip_count=completed_trip_count,
        cost_rows=cost_rows,
        completed_trips=completed_trips,
        maintenance_recent=maintenance_recent,
        vehicles=vehicles,
    )


if __name__ == "__main__":
    if not DATABASE.exists():
        initialize_database()
    ensure_schema_updates()
    seed_default_users()
    app.run(debug=True)
