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
    _migrate_capster_auth_columns()
    logger.info(f"Database initialized: {DATABASE_URL}")


def _migrate_capster_auth_columns():
    """Add new columns to existing tables if not yet exist (safe to re-run)."""
    is_sqlite = DATABASE_URL.startswith('sqlite')
    # (table, column, type)
    migrations = [
        ('capsters',      'username',      'VARCHAR(50)'),
        ('capsters',      'password_hash', 'VARCHAR(255)'),
        ('customers',     'visit_count',   'INTEGER DEFAULT 0'),
        ('customers',     'added_by',      "VARCHAR(100) DEFAULT ''"),
        ('transactions',  'customer_id',   'INTEGER'),
        ('services',      'commission_rate', 'REAL DEFAULT 0.5'),
    ]
    with engine.connect() as conn:
        for table, col, col_type in migrations:
            try:
                if is_sqlite:
                    conn.execute(__import__('sqlalchemy').text(
                        f'ALTER TABLE {table} ADD COLUMN {col} {col_type}'
                    ))
                else:
                    conn.execute(__import__('sqlalchemy').text(
                        f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}'
                    ))
                conn.commit()
                logger.info(f"Migration: added {table}.{col}")
            except Exception:
                # Column already exists — normal on second run
                conn.rollback()


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
