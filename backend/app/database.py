"""SQLAlchemy engine/session wiring.

Persistence is optional. If ``DB_ENABLED=false`` or MySQL is unreachable the
app still serves every stateless endpoint; DB-backed features degrade to an
in-process store. Nothing here raises at import time.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings
from app.logging_config import get_logger

log = get_logger(__name__)

Base = declarative_base()
engine: Engine | None = None
SessionLocal: sessionmaker | None = None
_db_ready = False


def _ensure_database_exists() -> None:
    import pymysql

    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        connect_timeout=5,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.db_name}")
        conn.commit()
    finally:
        conn.close()


def init_db() -> bool:
    """Best-effort DB bootstrap. Returns True if persistence is available."""
    global engine, SessionLocal, _db_ready

    if not settings.db_enabled:
        log.info("DB_ENABLED=false — persistence disabled.")
        return False
    try:
        _ensure_database_exists()
        engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=1800)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        # Imported here so models register against Base before create_all.
        from app import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        _db_ready = True
        log.info("Database ready at %s:%s/%s", settings.db_host, settings.db_port, settings.db_name)
    except Exception as exc:
        _db_ready = False
        log.warning("Database unavailable, running without persistence: %s", exc)
    return _db_ready


def db_ready() -> bool:
    return _db_ready


def get_db():
    """FastAPI dependency. Yields None when persistence is unavailable."""
    if not _db_ready or SessionLocal is None:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
