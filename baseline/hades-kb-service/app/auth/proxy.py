from fastapi import Request

from app.auth.errors import UnauthenticatedError


def get_credentials_via_proxy(request: Request) -> str:
    credentials = request.headers.get("Authorization")
    if credentials is None or credentials == "":
        raise UnauthenticatedError
    return credentials
