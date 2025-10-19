import base64
import csv
import os
import secrets
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List

from pdfminer.high_level import extract_text

from app.core.s3.bucket_util import (
    s3_upload_file,
)


def get_temporary_filename() -> str:
    """Returns a temporary filename. The filename is used to store data locally, so it must be using datetime and random"""
    return f"""{datetime.now(timezone.utc).strftime(
        'user-query %Y-%m-%d %H:%M:%S'
    )}{secrets.randbelow(100)}"""


def get_csv_delimiter(csv_content: str) -> str:
    """Get the main delimiter of the csv content"""
    sniffer = csv.Sniffer()
    return sniffer.sniff(csv_content).delimiter


def get_pdf_file_content(file_data: bytes) -> str:
    return extract_text(BytesIO(file_data))


def get_first_n_lines(data: str, number_of_lines: int) -> str:
    return "\n".join(data.splitlines()[:number_of_lines])


def delete_folder(foldername: str) -> None:
    folder_path = Path(foldername)

    # delete all the files inside the current folder
    for filename in os.listdir(foldername):
        folder_file_path = f"{foldername}/{filename}"
        Path.unlink(folder_file_path)

    if folder_path.is_dir():
        Path.rmdir(foldername)


def upload_folder_content_to_s3(folder_path: str) -> List[str]:
    files_generated_path: List[str] = []
    for filename in os.listdir(folder_path):
        folder_file_path = f"{folder_path}/{filename}"
        files_generated_path.append(folder_file_path)

        with Path.open(folder_file_path, "rb") as file_data:
            # Read the file and encode it into base64
            encoded_string = base64.b64encode(file_data.read()).decode()

            # Convert the base64 string back to bytes and to bytes io
            bytes_io_data = BytesIO(base64.b64decode(encoded_string))

            # upload the file to s3
            s3_upload_file(bytes_io_data, folder_file_path)
    return files_generated_path
