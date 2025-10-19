from typing import List

from fastapi import UploadFile

from app.core.s3.file_util import (
    get_file_size,
    is_valid_file_upload_type,
)

MAX_FILE_UPLOAD_SIZE = 20000000


async def check_upload_file_req(
    files: List[UploadFile], max_file_upload_size: int = MAX_FILE_UPLOAD_SIZE
) -> None:
    # check that file size is within 10mb
    for file in files:
        # check if the file types are supported for upload

        is_valid_file_upload_type(file.filename)

        file_size = await get_file_size(file)

        if file_size > max_file_upload_size:
            file_too_large_err = f"File size is too large, please upload a file that is less than {max_file_upload_size/1000000}mb"
            raise ValueError(file_too_large_err)
