from fastapi import HTTPException


class UnauthenticatedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=401, detail="You are not authenticated.")


class UnauthorizedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=403, detail="You are not authorized.")
