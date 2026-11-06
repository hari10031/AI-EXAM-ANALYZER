from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

# check_same_thread only applies to SQLite; harmless no-op guard for Postgres
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_phase03_columns(bind=engine) -> None:
    """create_all only creates missing tables, never new columns on existing tables —
    this upgrades a Phase 02 database in place (no migration framework at this scale)."""
    inspector = inspect(bind)
    if not inspector.has_table("questions"):
        return
    existing = {col["name"] for col in inspector.get_columns("questions")}
    with bind.begin() as conn:
        if "embedding" not in existing:
            conn.execute(text("ALTER TABLE questions ADD COLUMN embedding TEXT"))
        if "canonical_group_id" not in existing:
            conn.execute(text("ALTER TABLE questions ADD COLUMN canonical_group_id INTEGER"))
