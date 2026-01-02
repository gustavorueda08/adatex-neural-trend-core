import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

def get_db_engine() -> Engine:
    """
    Returns a SQLAlchemy Engine based on the environment.
    DEV -> SQLite (local file)
    PROD -> PostgreSQL (connection string from env)
    """
    env = os.getenv("ANTC_ENV", "DEV").upper()
    
    if env == "PROD":
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable is required in PROD mode.")
        return create_engine(db_url)
    else:
        # DEV mode: Use local SQLite
        # Using 3 slashes for relative path (current directory)
        return create_engine("sqlite:///antc_dev.db")
