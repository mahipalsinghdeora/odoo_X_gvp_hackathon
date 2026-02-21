from app import ensure_schema_updates, initialize_database, seed_default_users


if __name__ == "__main__":
    initialize_database()
    ensure_schema_updates()
    seed_default_users()
    print(
        "Database initialized. Default users: "
        "manager/manager123, dispatcher/dispatcher123, safety/safety123, finance/finance123"
    )
