import urllib
import urllib.parse
from io import BytesIO

import boto3

from app.core.config import app_config
from app.core.s3.constant import (
    GET_S3_MEDIA_ENDPOINT,
    HADES_KB_FILE_PATH,
)
from app.storage.ragdocument_db.constant import FILETYPE_UPLOAD_FILE


def s3_construct_file_path(filename: str, request_folder: str) -> str:
    # filename with "\" will mess up with the path when we are getting the file back from S3
    filename = filename.replace("\\", "_")
    return f"{HADES_KB_FILE_PATH}{request_folder}/{filename}"


def get_media_server_url(s3_file_path: str, file_type: str) -> str:
    """Returns a url to allow user to get the media by clicking on the url directly. Also escapes the s3 file path to allow the images to be displayed correctly."""
    if file_type != FILETYPE_UPLOAD_FILE:
        return ""

    return f"{app_config.server_base_url}{GET_S3_MEDIA_ENDPOINT}?s3_file_path={urllib.parse.quote_plus(s3_file_path)}"


def s3_upload_file(file_data: BytesIO, file_path: str) -> None:
    """Uploads a file to S3 bucket. Accepts the file data in bytes io"""
    s3 = boto3.client("s3")
    s3.upload_fileobj(file_data, app_config.s3_bucket_name, file_path)


def s3_get_file(s3_file_path: str) -> bytes:
    """Gets File from S3 bucket. Returns the file data in bytes."""
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=app_config.s3_bucket_name, Key=s3_file_path)
    return obj["Body"].read()
