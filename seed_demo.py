"""Seed demo fleet data if the database is empty (safe: only inserts when counts are 0)."""
import sqlite3
from datetime import date, timedelta

DB = "fleetflow.db"
conn = sqlite3.connect(DB)

def count(table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

today = date.today()

if count("vehicles") == 0:
    conn.executemany(
        "INSERT INTO vehicles (model_name, license_plate, max_capacity_kg, odometer, status) VALUES (?,?,?,?,?)",
        [
            ("Tata Ace Gold", "DL-01-AB-1001", 750, 42000, "On Trip"),
            ("Eicher Pro 2049", "DL-01-AB-1002", 4800, 96500, "On Trip"),
            ("Mahindra Bolero Pickup", "DL-01-AB-1003", 1000, 61000, "Available"),
            ("Ashok Leyland Dost", "DL-01-AB-1004", 1500, 128000, "In Shop"),
            ("Tata 407", "DL-01-AB-1005", 2500, 153000, "Available"),
        ],
    )

if count("drivers") == 0:
    conn.executemany(
        "INSERT INTO drivers (name, license_number, license_expiry_date, status, safety_score) VALUES (?,?,?,?,?)",
        [
            ("Ravi Kumar", "DL-2019-101", str(today + timedelta(days=400)), "On Trip", 88),
            ("Suresh Singh", "DL-2018-202", str(today + timedelta(days=20)), "On Trip", 64),
            ("Amit Verma", "DL-2020-303", str(today + timedelta(days=600)), "Available", 91),
            ("Deepak Yadav", "DL-2017-404", str(today - timedelta(days=15)), "Suspended", 42),
            ("Mohit Sharma", "DL-2021-505", str(today + timedelta(days=750)), "Available", 79),
        ],
    )

def vid(i): return i + 1
def did(i): return i + 1

if count("trips") == 0:
    conn.executemany(
        "INSERT INTO trips (vehicle_id, driver_id, cargo_weight, origin, destination, status, created_at) VALUES (?,?,?,?,?,?,?)",
        [
            (1, 1, 600, "Delhi", "Jaipur", "Dispatched", str(today - timedelta(days=1))),
            (2, 2, 4200, "Mumbai", "Pune", "Dispatched", str(today - timedelta(days=2))),
            (3, 3, 850, "Gurgaon", "Agra", "Draft", str(today)),
            (1, 1, 700, "Delhi", "Lucknow", "Completed", str(today - timedelta(days=5))),
            (5, 5, 2300, "Noida", "Kanpur", "Completed", str(today - timedelta(days=7))),
            (4, 4, 1400, "Faridabad", "Chandigarh", "Cancelled", str(today - timedelta(days=9))),
        ],
    )

if count("maintenance_logs") == 0:
    conn.executemany(
        "INSERT INTO maintenance_logs (vehicle_id, description, cost, date) VALUES (?,?,?,?)",
        [
            (4, "Engine overhaul", 28000, str(today - timedelta(days=2))),
            (2, "Brake pad replacement", 6400, str(today - timedelta(days=10))),
            (1, "Oil change", 3200, str(today - timedelta(days=20))),
            (5, "Tyre rotation", 1800, str(today - timedelta(days=45))),
            (3, "AC service", 4500, str(today - timedelta(days=75))),
        ],
    )

if count("fuel_logs") == 0:
    conn.executemany(
        "INSERT INTO fuel_logs (vehicle_id, liters, cost, date) VALUES (?,?,?,?)",
        [
            (1, 28.5, 2720, str(today - timedelta(days=1))),
            (2, 145.0, 13800, str(today - timedelta(days=2))),
            (3, 34.0, 3200, str(today - timedelta(days=4))),
            (5, 68.0, 6450, str(today - timedelta(days=6))),
            (1, 25.0, 2380, str(today - timedelta(days=8))),
            (4, 30.0, 2850, str(today - timedelta(days=12))),
        ],
    )

conn.commit()
conn.close()
print("seeded")
