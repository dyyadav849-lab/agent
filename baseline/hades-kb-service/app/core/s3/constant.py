from enum import Enum

GET_S3_MEDIA_ENDPOINT = "/s3/get-s3-media"

HADES_KB_FILE_PATH = "hades-kb-s3-storage"


class FileType(Enum):
    TXT = ".txt"
    CSV = ".csv"
    DOCX = ".docx"
    XLSX = ".xlsx"
    XLS = ".xls"
    PDF = ".pdf"
