from logging.config import fileConfig
import sys
from os.path import abspath, dirname

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Ensure workspace root is in Python search path to import 'backend' packages
sys.path.insert(0, dirname(dirname(dirname(dirname(abspath(__file__))))))


from backend.core.config import settings
from backend.core.database import Base
from backend.modules.contracts import models as _
from backend.modules.trust_score import models as _
from backend.modules.anomaly import models as _
from backend.modules.incidents import models as _
from backend.modules.lineage import models as _
from backend.modules.profiling import models as _
from backend.modules.ingestion import models as _
from backend.modules.timeline import models as _
from backend.modules.alerts import models as _
from backend.modules.users import models as _

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the sqlalchemy.url dynamically from application settings
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

# target_metadata is the metadata of Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    url = config.get_main_option("sqlalchemy.url")
    if url and url.startswith("sqlite"):
        import os
        from sqlalchemy import event
        workspace_root = dirname(dirname(dirname(dirname(abspath(__file__)))))
        public_silver_path = os.path.join(workspace_root, "public_silver.db")
        test_results_path = os.path.join(workspace_root, "test_results.db")
        
        @event.listens_for(connectable, "connect")
        def connect(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute(f"ATTACH DATABASE '{public_silver_path.replace(chr(92), chr(47))}' AS public_silver")
            cursor.execute(f"ATTACH DATABASE '{test_results_path.replace(chr(92), chr(47))}' AS test_results")
            cursor.close()

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
