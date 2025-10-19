from typing import Dict

from app.auth.sessions.abstract_session_store import AbstractSessionStore


# NoopSessionStore is a no-op implementation for the session store
class NoopSessionStore(AbstractSessionStore):
    def __init__(self) -> None:
        pass

    def get_session_token(self, _key: str, _field: Dict) -> str:
        return ""

    def set_session_token(self, key: str, field: str, value: str) -> None:
        pass

    def set_expiry(self, key: str, expiry_unix_timestamp_seconds: int) -> None:
        pass

    def clear(self, key: str) -> None:
        pass
