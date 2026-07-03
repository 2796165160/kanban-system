import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # "sqlite" or "postgresql"

if DB_TYPE == "postgresql":
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "kanban")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "postgres")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "data.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={} if DB_TYPE == "postgresql" else {"check_same_thread": False, "timeout": 30},
)
SessionLocal = sessionmaker(bind=engine)


def enable_wal():
    """Enable WAL mode for SQLite for better concurrent access."""
    if DB_TYPE == "sqlite":
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA busy_timeout=30000"))
            conn.commit()


class Base(DeclarativeBase):
    pass


def run_migrations():
    """Add missing columns to existing tables without dropping data."""
    conn = engine.connect()
    inspector = inspect(conn)
    # Platform: add base_url, access_key
    cols = [c["name"] for c in inspector.get_columns("platforms")]
    if "base_url" not in cols:
        conn.execute(text("ALTER TABLE platforms ADD COLUMN base_url VARCHAR(500) DEFAULT ''"))
    if "access_key" not in cols:
        conn.execute(text("ALTER TABLE platforms ADD COLUMN access_key VARCHAR(255) DEFAULT ''"))
    if "schedule_times" not in cols:
        conn.execute(text("ALTER TABLE platforms ADD COLUMN schedule_times VARCHAR(200) DEFAULT ''"))
    # Project: add project_key
    pcols = [c["name"] for c in inspector.get_columns("projects")]
    if "project_key" not in pcols:
        conn.execute(text("ALTER TABLE projects ADD COLUMN project_key VARCHAR(255) DEFAULT ''"))
    # Task: add task_key
    tcols = [c["name"] for c in inspector.get_columns("tasks")]
    if "task_key" not in tcols:
        conn.execute(text("ALTER TABLE tasks ADD COLUMN task_key VARCHAR(255) DEFAULT ''"))
    conn.commit()
    conn.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
