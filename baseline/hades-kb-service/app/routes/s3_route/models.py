from pydantic import BaseModel


class ServeFileData(BaseModel):
    file_content: bytes
    request_header: dict
    media_type: str
