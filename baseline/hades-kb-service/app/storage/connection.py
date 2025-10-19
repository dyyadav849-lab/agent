from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import app_config

# Replace with your actual configuration
DATABASE_URL = f"postgresql+psycopg2://{app_config.postgres_db_user}:{app_config.postgres_db_password}@{app_config.postgres_db_host}:{app_config.postgres_db_port}/{app_config.postgres_db_name}"

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    max_overflow=app_config.postgres_max_overflow,  # Maximum number of connections to allow in connection pool
    pool_size=app_config.postgres_pool_size,  # Number of connections to keep open within the connection pool
    pool_timeout=app_config.postgres_pool_timeout,  # Specifies the number of seconds to wait before giving a connection pool timeout error
    pool_recycle=app_config.postgres_pool_recycle,  # Number of seconds a connection can persist before being recycled. Helps in handling DBAPI connections that are inactive on the server side.
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.begin()
        yield db
    except Exception as e:
        db.rollback()
        error_message = "db operation failed, rollback."
        raise Exception(error_message) from e
    finally:
        db.close()
