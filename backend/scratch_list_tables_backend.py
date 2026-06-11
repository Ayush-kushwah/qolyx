import sqlite3
import os

for path in ["qolyx_local.db", "../qolyx_local.db"]:
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        print(f"\nTables in {os.path.abspath(path)}:")
        for r in cursor.fetchall():
            print(f" - {r[0]}")
        conn.close()
