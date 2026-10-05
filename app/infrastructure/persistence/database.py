"""SQLAlchemy engine and session construction."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str) -> Engine:
    """Create an engine with SQLite's local connection setting when applicable."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions that keep loaded ORM values available after commit."""
    return sessionmaker(bind=engine, expire_on_commit=False)
