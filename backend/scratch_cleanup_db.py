import sqlite3
import os

db_path = "../qolyx_local.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables_to_drop = [
        "integration_connections", 
        "users", 
        "user_sessions", 
        "user_login_history", 
        "user_api_keys"
    ]
    for table in tables_to_drop:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"Dropped table {table} if it existed.")
        except Exception as e:
            print(f"Error dropping {table}: {e}")
    conn.commit()
    conn.close()
    print("Database cleanup completed.")
else:
    print(f"Database {db_path} does not exist.")
