import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.log.logger import Logger
from app.core.s3.constant import GET_S3_MEDIA_ENDPOINT
from app.routes.s3_route.handler import get_s3_file_content, serve_s3_media_handler
from app.routes.s3_route.models import ServeFileData
from app.routes.slack_kb_route.response_config import open_api_config

s3_storage_route = APIRouter()
logger = Logger(name="s3_route_controller")


@s3_storage_route.get(
    "/s3/get-s3-file-content",
    responses=open_api_config,
    summary="Allows user to call the endpoint and pass in the path to the S3 file. The file content will be returned back to user",
)
async def get_s3_file_content(
    result: ServeFileData = Depends(get_s3_file_content),
) -> dict:
    return result


@s3_storage_route.get(
    GET_S3_MEDIA_ENDPOINT,
    responses=open_api_config,
    summary="Allows user to call the endpoint and pass in the path to the S3 file. The file content will be streamed back to user, allowing them to download the file",
)
async def serve_media(
    result: ServeFileData = Depends(serve_s3_media_handler),
) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(result.file_content),
        headers=result.request_header,
        media_type=result.media_type,
    )
