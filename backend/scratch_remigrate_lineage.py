import sqlite3
import os
import subprocess

db_path = "qolyx_local.db"
print(f"Connecting to database: {db_path} (exists: {os.path.exists(db_path)})")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Drop lineage tables
    tables = ["lineage_edge_history", "lineage_edges", "lineage_nodes"]
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"Dropped table: {table}")
        except Exception as e:
            print(f"Failed to drop table {table}: {e}")
            
    # 2. Delete migration version from alembic_version
    try:
        cursor.execute("DELETE FROM alembic_version WHERE version_num = '03e4d60d721e'")
        print("Removed migration version 03e4d60d721e from alembic_version.")
    except Exception as e:
        print(f"Failed to clear alembic version: {e}")
        
    conn.commit()
    conn.close()
    
# 3. Run alembic upgrade head
try:
    print("Re-applying migration...")
    env = os.environ.copy()
    
    # Load .env file manually from workspace root
    dotenv_path = ".env"
    if os.path.exists(dotenv_path):
        with open(dotenv_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
                    
    env["DATABASE_URL"] = "sqlite:///C:/Users/capta/OneDrive/Desktop/qolyx/qolyx_local.db"
    
    subprocess.run(["alembic", "upgrade", "head"], env=env, cwd="backend", check=True)
    print("Migrations successfully applied.")
except Exception as e:
    print(f"Error running migrations: {e}")
