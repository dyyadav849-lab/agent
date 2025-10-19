from fastapi import HTTPException

from app.core.log.logger import Logger
from app.core.s3.bucket_util import (
    s3_get_file,
)
from app.core.s3.file_util import (
    get_filename,
    get_media_mime_type,
)
from app.routes.s3_route.models import ServeFileData

logger = Logger(name="s3_route_handler")


def serve_s3_media_handler(s3_file_path: str) -> ServeFileData:
    """
    gets the file from S3 bucket, and returns response for user as byte.

    For other file types, the response will be streamed back so user can redownload the file
    """
    try:
        return ServeFileData(
            file_content=s3_get_file(s3_file_path),
            request_header={
                "Content-Disposition": f'attachment; filename="{get_filename(s3_file_path)}"'
            },
            media_type=get_media_mime_type(s3_file_path),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unable to get file data from S3 with error: {e}"
        ) from e


def get_s3_file_content(s3_file_path: str) -> dict:
    """
    gets the file from S3 bucket, and returns string of the file as response

    """
    try:
        return {"file_content": s3_get_file(s3_file_path)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unable to get file data from S3 with error: {e}"
        ) from e
