from enum import Enum


# SessionAuthMode controls for which auth mode to use for session management
class SessionAuthMode(Enum):
    PROXY = "proxy"
    WEB = "web"
    BACKEND = "backend"


# get_session_auth_mode returns to current configured session mode, defaults to PROXY mode
def get_session_auth_mode(raw_auth_mode: str) -> SessionAuthMode:
    match raw_auth_mode:
        case raw_auth_mode if raw_auth_mode.lower() == SessionAuthMode.WEB.value:
            return SessionAuthMode.WEB
        case raw_auth_mode if raw_auth_mode.lower() == SessionAuthMode.BACKEND.value:
            return SessionAuthMode.BACKEND
        case _:
            return SessionAuthMode.PROXY
