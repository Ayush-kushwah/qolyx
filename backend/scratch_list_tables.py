import sqlite3
import os

db_path = "../qolyx_local.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Main database tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Main Database Tables:")
for r in cursor.fetchall():
    print(r[0])

# Attach others
try:
    cursor.execute("ATTACH DATABASE '../public_silver.db' AS public_silver")
    cursor.execute("SELECT name FROM public_silver.sqlite_master WHERE type='table';")
    print("\npublic_silver Database Tables:")
    for r in cursor.fetchall():
        print(r[0])
except Exception as e:
    print(f"Error reading public_silver: {e}")

try:
    cursor.execute("ATTACH DATABASE '../test_results.db' AS test_results")
    cursor.execute("SELECT name FROM test_results.sqlite_master WHERE type='table';")
    print("\ntest_results Database Tables:")
    for r in cursor.fetchall():
        print(r[0])
except Exception as e:
    print(f"Error reading test_results: {e}")

conn.close()
