from collections.abc import Generator
from typing import Any, Callable, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.log.logger import Logger
from app.routes.doc_kb_route.handler import (
    create_new_document_collection,
    get_document_collection_metadata,
    ingest_new_doc_content,
    ingest_new_doc_content_stream_handler,
    ingest_new_doc_invoke_handler,
    ingest_new_doc_stream_handler,
    search_document_knowledge_base,
    update_document_collection,
    update_document_collection_mapping,
    update_document_information,
)
from app.routes.doc_kb_route.models import (
    CreateDocumentCollectionModel,
    DocumentCollectionMetadata,
    DocumentCollectionModel,
    DocumentInformationModel,
    IngestNewDocumentContentResponse,
    SearchKnowledgeBaseResult,
    UploadDocumentResponse,
)
from app.routes.slack_kb_route.response_config import open_api_config

doc_kb_route = APIRouter()
logger = Logger(name="doc_kb_route_controller")


@doc_kb_route.post(
    "/doc_kb_route/ingest_new_doc",
    responses=open_api_config,
    summary="Allows user to ingest a list ofn new documents, and save it to knowledge base",
)
async def ingest_new_doc_handler(
    result: UploadDocumentResponse = Depends(ingest_new_doc_invoke_handler),
) -> UploadDocumentResponse:
    return result


@doc_kb_route.post(
    "/doc_kb_route/ingest_new_doc_stream",
    responses=open_api_config,
    summary="Allows user to ingest a list ofn new documents, and save it to knowledge base",
)
async def ingest_new_doc_handler_stream_endpoint(
    stream_response: Callable[[None], Generator[str, Any, Any]] = Depends(
        ingest_new_doc_stream_handler
    ),
) -> StreamingResponse:
    return StreamingResponse(stream_response())


@doc_kb_route.post(
    "/doc_kb_route/ingest_new_doc_content",
    responses=open_api_config,
    summary="Allows user to ingest new doc based on passed in document content",
)
async def ingest_new_doc_content(
    result: IngestNewDocumentContentResponse = Depends(ingest_new_doc_content),
) -> IngestNewDocumentContentResponse:
    doc_information_result = await result
    return IngestNewDocumentContentResponse(
        document_information=doc_information_result.__dict__, status="OK"
    )


@doc_kb_route.post(
    "/doc_kb_route/ingest_new_doc_content_stream",
    responses=open_api_config,
    summary="Allows user to ingest new doc based on passed in document content",
)
async def ingest_new_doc_content_stream(
    stream_response: Callable[[None], Generator[str, Any, Any]] = Depends(
        ingest_new_doc_content_stream_handler
    ),
) -> DocumentInformationModel:
    return StreamingResponse(stream_response())


@doc_kb_route.post(
    "/doc_kb_route/create_new_document_collection",
    responses=open_api_config,
    summary="Allows user to create a new document collection, aka a list of documents",
)
async def create_new_document_collection(
    result: CreateDocumentCollectionModel = Depends(create_new_document_collection),
) -> DocumentCollectionModel:
    return result


@doc_kb_route.post(
    "/doc_kb_route/update_document_collection",
    responses=open_api_config,
    summary="Allows user to update information on existing document collection, such as updating the name, description, status",
)
async def update_document_collection(
    result: dict = Depends(update_document_collection),
) -> dict:
    return result


@doc_kb_route.post(
    "/doc_kb_route/search_document_knowledge_base",
    responses=open_api_config,
    summary="Allows user to search based on existing document knowledge base",
)
async def search_document_knowledge_base(
    result: list[SearchKnowledgeBaseResult] = Depends(search_document_knowledge_base),
) -> Dict[str, list[SearchKnowledgeBaseResult]]:
    return result


@doc_kb_route.post(
    "/doc_kb_route/update_document_information",
    responses=open_api_config,
    summary="Allows user to update document information status",
)
async def update_document_information(
    result: dict = Depends(update_document_information),
) -> dict:
    return result


@doc_kb_route.post(
    "/doc_kb_route/update_document_collection_mapping",
    responses=open_api_config,
    summary="Allows user to update if a document should be added inside a document collection by setting the status",
)
async def update_document_collection_mapping(
    result: dict = Depends(update_document_collection_mapping),
) -> dict:
    return result


@doc_kb_route.get(
    "/doc_kb_route/get_document_collection_metadata",
    responses=open_api_config,
    summary="Allows to get all the document inside a document based on a document collection UUID",
)
async def get_document_collection_metadata(
    result: DocumentCollectionMetadata = Depends(get_document_collection_metadata),
) -> DocumentCollectionMetadata:
    return result
