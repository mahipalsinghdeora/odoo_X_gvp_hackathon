DROP TABLE IF EXISTS maintenance_logs;
DROP TABLE IF EXISTS fuel_logs;
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS drivers;
DROP TABLE IF EXISTS vehicles;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    name TEXT,
    email TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Manager', 'Dispatcher', 'Safety Officer', 'Financial Analyst')),
    status TEXT NOT NULL DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'rejected'))
);

CREATE TABLE vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    license_plate TEXT NOT NULL UNIQUE,
    max_capacity_kg REAL NOT NULL CHECK (max_capacity_kg > 0),
    odometer INTEGER NOT NULL CHECK (odometer >= 0),
    status TEXT NOT NULL CHECK (status IN ('Available', 'On Trip', 'In Shop'))
);

CREATE TABLE drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    license_number TEXT NOT NULL UNIQUE,
    license_expiry_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Available', 'On Trip', 'Suspended')),
    safety_score INTEGER NOT NULL DEFAULT 75 CHECK (safety_score >= 0 AND safety_score <= 100)
);

CREATE TABLE trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    cargo_weight REAL NOT NULL CHECK (cargo_weight > 0),
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Draft', 'Dispatched', 'Completed', 'Cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE RESTRICT
);

CREATE TABLE maintenance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    cost REAL NOT NULL CHECK (cost >= 0),
    date TEXT NOT NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT
);

CREATE TABLE fuel_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,
    liters REAL NOT NULL CHECK (liters > 0),
    cost REAL NOT NULL CHECK (cost >= 0),
    date TEXT NOT NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT
);
