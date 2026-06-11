import os
import shutil
import sqlite3

workspace_root = r"c:\Users\capta\OneDrive\Desktop\qolyx"
backend_db = os.path.join(workspace_root, "backend", "qolyx_local.db")
root_db = os.path.join(workspace_root, "qolyx_local.db")

print(f"Backend DB exists: {os.path.exists(backend_db)}")
print(f"Root DB exists: {os.path.exists(root_db)}")

# Copy backend DB to root DB
if os.path.exists(backend_db):
    shutil.copy2(backend_db, root_db)
    print("Copied backend database to root workspace database.")
    os.remove(backend_db)
    print("Deleted backend database.")

# List tables in root database to verify
conn = sqlite3.connect(root_db)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("\nTables in root database:")
for r in cursor.fetchall():
    print(f" - {r[0]}")
conn.close()
