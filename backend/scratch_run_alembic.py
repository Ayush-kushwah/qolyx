import os
import subprocess

# Load .env file manually relative to script location
env = os.environ.copy()
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(dotenv_path):
    with open(dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()


# Override DATABASE_URL to use the absolute path of the root SQLite database
env["DATABASE_URL"] = "sqlite:///C:/Users/capta/OneDrive/Desktop/qolyx/qolyx_local.db"

try:
    print("Applying migration using absolute path to root database...")
    # Run from the backend directory so alembic finds alembic.ini
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.run(["alembic", "upgrade", "head"], env=env, cwd=backend_dir, check=True)
    print("Successfully applied migration to head.")
except Exception as e:
    print(f"Error running alembic: {e}")

