import mimetypes
from io import BytesIO

import docx
import pandas as pd
from fastapi import UploadFile
from pdfminer.high_level import extract_text

from app.core.s3.constant import FileType


def get_pdf_file_content(file_data: bytes) -> str:
    return extract_text(BytesIO(file_data))


def is_valid_file_upload_type(filename: str) -> None:
    supported_file_type = (
        FileType.TXT.value,
        FileType.CSV.value,
        FileType.DOCX.value,
        FileType.XLSX.value,
        FileType.PDF.value,
        FileType.XLS.value,
    )
    if not filename.endswith(supported_file_type):
        invalid_file_type = f"Only {supported_file_type} files are supported"
        raise ValueError(invalid_file_type)


def get_file_type(filename: str) -> str:
    """Gets the filetype for a given filename
    Will throw an error if the file type is not supported
    """
    for file_type in FileType:
        if filename.endswith(file_type.value):
            return file_type.value
    valid_file_types = ",".join([valid_file_type.value for valid_file_type in FileType])
    invalid_file_name_err = f"Only {valid_file_types} files are supported"
    raise ValueError(invalid_file_name_err)


def get_file_content_from_bytes(file_content: bytes, filename: str) -> str:
    file_type = get_file_type(filename)
    match file_type:
        case FileType.TXT.value | FileType.CSV.value:
            return file_content.decode("utf-8")
        case FileType.DOCX.value:
            document_data = docx.Document(BytesIO(file_content))
            return "\n".join([paragraph.text for paragraph in document_data.paragraphs])
        case FileType.PDF.value:
            return get_pdf_file_content(file_content)
        case FileType.XLS.value | FileType.XLSX.value:
            panda_excel_data = pd.ExcelFile(BytesIO(file_content))
            content_to_return = ""
            for sheet_name in panda_excel_data.sheet_names:
                # Load a sheet into a DataFrame by name
                dataframe = panda_excel_data.parse(sheet_name)

                file_data = dataframe.to_csv(index=False)

                content_to_return += file_data
            return content_to_return

    # default just convert to string before return
    return str(file_content)


async def get_file_size(file: UploadFile) -> int:
    """Gets the filesize in bytes for a given file"""
    content = await file.read()
    size = len(content)

    # reset file pointer to the beginning
    await file.seek(0)

    return size


def get_media_mime_type(filename: str) -> str:
    """Gets the media mime type, based on the given filename"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type


def get_filename(s3_file_path: str) -> str:
    return s3_file_path.split("/")[-1]
