"""
Database engine and session factory.
DATABASE_URL defaults to SQLite. Set env var to use PostgreSQL.
"""
import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.db.models import Base

logger = logging.getLogger(__name__)

# Auto-fix Render.com postgres:// → postgresql://
_raw_url = os.getenv('DATABASE_URL', 'sqlite:///./barbershop.db')
DATABASE_URL = _raw_url.replace('postgres://', 'postgresql://', 1)

_connect_args = {}
if DATABASE_URL.startswith('sqlite'):
    _connect_args = {
        'check_same_thread': False,
        'timeout': 30,          # detik — tunggu write lock sebelum raise OperationalError
    }

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

# Enable WAL mode + busy_timeout untuk SQLite
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA busy_timeout=30000')   # ms — redundant safety net
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db():
    """Create all tables (dev / first-run without Alembic)."""
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized: {DATABASE_URL}")


@contextmanager
def get_db() -> Session:
    """Yield a database session with auto commit/rollback."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
