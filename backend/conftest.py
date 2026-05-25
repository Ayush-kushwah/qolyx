import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Global hook to ensure that any SQLite in-memory database used during testing
    automatically has the 'public_silver' database attached, satisfying the schema
    requirements of the read-only SilverAnomalyFeature model.
    """
    try:
        # Check if the connection is indeed a SQLite connection
        if "sqlite" in type(dbapi_connection).__module__:
            cursor = dbapi_connection.cursor()
            cursor.execute("ATTACH DATABASE ':memory:' AS public_silver")
            cursor.close()
    except Exception:
        pass
