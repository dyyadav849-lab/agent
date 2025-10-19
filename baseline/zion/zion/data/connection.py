from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from zion.config import global_config

DATABASE_URL = f"mysql+pymysql://{global_config.mysql_db_user}:{global_config.mysql_db_password}@{global_config.mysql_db_host}:{global_config.mysql_db_port}/{global_config.mysql_db_name}"

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    max_overflow=10,  # Maximum number of connections to allow in connection pool
    pool_size=3,  # Number of connections to keep open within the connection pool
    pool_timeout=30,  # Specifies the number of seconds to wait before giving a connection pool timeout error
    pool_recycle=1800,  # Number of seconds a connection can persist before being recycled. Helps in handling DBAPI connections that are inactive on the server side.
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
        raise Exception(error_message) from e  # noqa:TRY002 message-create your own exception
    finally:
        db.close()
