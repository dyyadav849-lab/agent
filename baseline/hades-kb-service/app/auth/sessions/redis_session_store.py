import base64
import hashlib

from redis.cluster import RedisCluster as Redis

from app.auth.modes import SessionAuthMode, get_session_auth_mode
from app.auth.sessions.abstract_session_store import AbstractSessionStore
from app.auth.sessions.noop_session_store import NoopSessionStore
from app.core.config import app_config


# RedisSessionStore implements the session store with redis as a backend storage
# a valid redis cluster must be available for use with this session storage strategy
class RedisSessionStore(AbstractSessionStore):
    def __init__(self, session_secret_key: str) -> None:
        self.session_secret_key = session_secret_key
        redis_cli = Redis(host=app_config.redis_host, port=app_config.redis_port)
        self.redis_cli = redis_cli

    def get_session_token(self, key: str, field: str) -> str:
        session_id = self.__get_session_key(key)
        result = self.redis_cli.hget(session_id, field)
        token = ""
        if result is not None:
            # decode to str as stored value is in bytes
            token = result.decode("utf-8")
        return token

    def set_session_token(self, key: str, field: str, value: str) -> None:
        session_id = self.__get_session_key(key)
        self.redis_cli.hset(session_id, field, value)

    def set_expiry(self, key: str, expiry_unix_timestamp_seconds: int) -> None:
        session_id = self.__get_session_key(key)
        self.redis_cli.expireat(session_id, expiry_unix_timestamp_seconds)

    def clear(self, key: str) -> None:
        session_id = self.__get_session_key(key)
        self.redis_cli.delete(session_id)

    # internal reusable function to get the session key
    def __get_session_key(self, username: str) -> str:
        session_id = hashlib.sha256()
        session_id.update(username.encode("utf-8"))
        session_id.update(self.session_secret_key.encode("utf-8"))
        session_id_bytes = base64.b64encode(session_id.digest())
        return session_id_bytes.decode("utf-8")


redis_session_store = NoopSessionStore()
if get_session_auth_mode(app_config.auth_mode) == SessionAuthMode.BACKEND:
    redis_session_store = RedisSessionStore(app_config.session_secret_key)
