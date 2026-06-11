import sqlite3
import os

db_path = "../qolyx_local.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute("DROP TABLE IF EXISTS integration_connections")
    conn.commit()
    print("Dropped integration_connections from root DB.")
except Exception as e:
    print(f"Error: {e}")
conn.close()
