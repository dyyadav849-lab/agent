from typing import List

from fastapi.exceptions import RequestValidationError
from pydantic import (
    BaseModel,
    model_validator,
)

from app.storage.ragdocument_db.constant import ACTIVE_STATUS, INACTIVE_STATUS


class DocumentKnowledgeBaseFilter(BaseModel):
    document_collection_uuids: List[str]


class DocumentKnowledgeBaseRequestModel(BaseModel):
    filter: DocumentKnowledgeBaseFilter
    query: str = ""

    @model_validator(mode="before")
    @classmethod
    def validate_request_body(cls, value: dict) -> dict:
        message = "missing fields:"
        is_missing = False
        filter_dict: dict = value.get("filter")

        if not str(value.get("query", "")).strip():
            message = f"{message}{',' if is_missing else ''} query"
            is_missing = True

        if filter_dict is None:
            message = (
                f"{message} filter_dict is compulsory for searching knowledge base"
            )
            is_missing = True

        if len(filter_dict.get("document_collection_uuids", [])) <= 0:
            message = f"{message}{',' if is_missing else ''} filter_dict.document_collection_uuids"
            is_missing = True

        if is_missing:
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        return value


class FileMetadata(BaseModel):
    filename: str
    file_content_byte: bytes
    file_content: str
    file_path: str


class DocumentEmbeddingResponse(BaseModel):
    token_number: int
    document_information_id: int
    text_snipplet: str
    status: str


class DocumentInformationModel(BaseModel):
    filename: str
    id: int
    file_path: str
    file_type: str
    status: str
    document_last_updated: str


class SearchKnowledgeBaseResult(BaseModel):
    document_embedding: DocumentEmbeddingResponse
    document_information: DocumentInformationModel


class DocumentInformationRequestModel(BaseModel):
    id: int
    status: str

    @model_validator(mode="before")
    @classmethod
    def validate_request_body(cls, value: dict) -> dict:
        message = "missing fields:"
        is_missing = False

        if not str(value.get("status", "")).strip():
            message = f"{message}{',' if is_missing else ''} status"
            is_missing = True

        if value.get("id", 0) <= 0:
            message = f"{message}{',' if is_missing else ''} id"
            is_missing = True

        if is_missing:
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        if value.get("status", "") not in [ACTIVE_STATUS, INACTIVE_STATUS]:
            raise RequestValidationError(
                errors=f"status must be one of the values: {[ACTIVE_STATUS, INACTIVE_STATUS]}"
            )

        return value


class IngestDocumentContentRequest(BaseModel):
    document_content: str
    document_uri: str
    filename: str
    document_collection_uuid: str

    @model_validator(mode="before")
    @classmethod
    def validate_request_body(cls, value: dict) -> dict:
        message = "missing fields:"
        is_missing = False

        if not str(value.get("document_content", "")).strip():
            message = f"{message}{',' if is_missing else ''} document_content"
            is_missing = True

        if not str(value.get("document_uri", "")).strip():
            message = f"{message}{',' if is_missing else ''} document_uri"
            is_missing = True

        if not str(value.get("filename", "")).strip():
            message = f"{message}{',' if is_missing else ''} filename"
            is_missing = True

        if not str(value.get("document_collection_uuid", "")).strip():
            message = f"{message}{',' if is_missing else ''} document_collection_uuid"
            is_missing = True

        if is_missing:
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        return value


class DocumentCollectionMappingModel(BaseModel):
    document_information_id: int
    document_collection_uuid: str
    status: str

    @model_validator(mode="before")
    @classmethod
    def validate_request_body(cls, value: dict) -> dict:
        message = "missing fields:"
        is_missing = False

        if value.get("document_information_id", 0) <= 0:
            message = f"{message}{',' if is_missing else ''} document_information_id"
            is_missing = True

        if not str(value.get("document_collection_uuid", "")).strip():
            message = f"{message}{',' if is_missing else ''} document_collection_uuid"
            is_missing = True

        if not str(value.get("status", "")).strip():
            message = f"{message}{',' if is_missing else ''} status"
            is_missing = True

        if is_missing:
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        return value


class CreateDocumentCollectionModel(BaseModel):
    name: str
    description: str
    status: str = ACTIVE_STATUS

    @model_validator(mode="before")
    @classmethod
    def validate_request_body(cls, value: dict) -> dict:
        message = "missing fields:"
        is_missing = False

        if not str(value.get("name", "")).strip():
            message = f"{message}{',' if is_missing else ''} name"
            is_missing = True

        if is_missing:
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        return value


class DocumentCollectionModel(BaseModel):
    uuid: str
    name: str
    description: str
    status: str = ACTIVE_STATUS

    @model_validator(mode="before")
    @classmethod
    def validate_request_body(cls, value: dict) -> dict:
        message = "missing fields:"
        is_missing = False

        if not str(value.get("name", "")).strip():
            message = f"{message}{',' if is_missing else ''} name"
            is_missing = True

        if not str(value.get("uuid", "")).strip():
            message = f"{message}{',' if is_missing else ''} uuid"
            is_missing = True

        if is_missing:
            raise RequestValidationError(errors=f"{message} | request body: {value}")

        return value


# a document could be enabled, but might be disabled from a document collection
class DocumentCollectionMappingMetadata(BaseModel):
    status: str
    document_information: DocumentInformationModel


class DocumentCollectionMetadata(BaseModel):
    document_collection_metadata: DocumentCollectionModel
    document_informations: List[DocumentCollectionMappingMetadata]


class UploadDocumentResponse(BaseModel):
    status: str
    files: List[dict]


class IngestNewDocumentContentResponse(BaseModel):
    status: str
    document_information: dict | None
