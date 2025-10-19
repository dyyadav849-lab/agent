from datetime import datetime, timezone
from typing import Optional

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.log.logger import Logger


class BaseResponse(BaseModel):
    message: str = "Success"
    error: bool = False
    details: str = ""


def get_exception_action_response(
    e: Exception,
    logger: Logger,
    name: str,
    response: BaseResponse,
    tags: Optional[dict] = None,
) -> JSONResponse:
    tags = tags if tags else {}

    tags["timestamp"] = datetime.now(timezone.utc)

    logger.exception(" ".join([f"{name} Error:", str(e)]), tags=tags)

    response.details = e.args[0] if len(e.args) != 0 else str(e)
    response.error = True

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(response),
    )


def is_float(s: str) -> bool:
    try:
        _ = float(s)
        return True  # noqa: TRY300: moving this statement to else block does not apply
    except ValueError:
        return False
