import abc


class AbstractSessionStore(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_session_token(self, key: str, field: str) -> str:
        return ""

    @abc.abstractmethod
    def set_session_token(self, key: str, field: str, value: str) -> None:
        pass

    @abc.abstractmethod
    def set_expiry(self, key: str, expiry_unix_timestamp_seconds: int) -> None:
        pass

    @abc.abstractmethod
    def clear(self, key: str) -> None:
        pass
