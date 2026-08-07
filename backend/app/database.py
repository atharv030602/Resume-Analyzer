import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _ensure_database_exists() -> None:
    """Mirrors Spring's createDatabaseIfNotExist=true — creates the DB on first run."""
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.db_name}")
        conn.commit()
    finally:
        conn.close()


try:
    _ensure_database_exists()
except Exception as e:
    # MySQL unreachable locally (broken install) — TEMP: skip so the agentic/upload
    # endpoints (which don't touch the DB) still work. /api/analyze will fail until fixed.
    print(f"WARNING: could not reach MySQL, DB features disabled: {e}")

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
