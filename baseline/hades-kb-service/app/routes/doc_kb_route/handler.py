import asyncio
import io
import time
from asyncio import AbstractEventLoop
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List

from fastapi import Depends, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import app_config
from app.core.dependencies import get_ragdocument
from app.core.log.logger import Logger
from app.core.ragdocument.client import RagDocumentClient
from app.core.s3.bucket_util import (
    get_media_server_url,
    s3_construct_file_path,
    s3_upload_file,
)
from app.core.s3.file_util import get_file_content_from_bytes
from app.models.utils import num_tokens_from_string
from app.routes.doc_kb_route.models import (
    CreateDocumentCollectionModel,
    DocumentCollectionMappingModel,
    DocumentCollectionMetadata,
    DocumentCollectionModel,
    DocumentInformationModel,
    DocumentInformationRequestModel,
    DocumentKnowledgeBaseRequestModel,
    FileMetadata,
    IngestDocumentContentRequest,
    IngestNewDocumentContentResponse,
    SearchKnowledgeBaseResult,
    UploadDocumentResponse,
)
from app.routes.utils import BaseResponse, get_exception_action_response
from app.storage.ragdocument_db.constant import (
    FILETYPE_FILE_CONTENT,
    FILETYPE_UPLOAD_FILE,
)
from app.storage.ragdocument_db.models import (
    DocumentEmbedding,
    DocumentInformation,
)
from app.utils.endpoint_helper import check_upload_file_req
from app.utils.file_handler import (
    get_temporary_filename,
)

logger = Logger(name="ingest_doc_route")

STATUS_OK = {"status": "OK"}


def __check_rag_document_secret(request: Request) -> None:
    """Checks if the given request header contains an rag-document-secret secret
    Also, checks if the rag-document-secret secret provided is valid and is defined inside the config
    """
    if "rag-document-secret" not in request.headers:
        message = "rag-document-secret is missing"
        raise HTTPException(401, message)

    if request.headers["rag-document-secret"] != app_config.document_rag_secret_key:
        message = "Invalid rag-document-secret"
        raise HTTPException(401, message)


def update_document_collection_mapping(
    request: Request,
    request_input: DocumentCollectionMappingModel,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> dict:
    __check_rag_document_secret(request)
    try:
        ragdocument.update_document_collection_mapping(request_input)

    except Exception as e:  # noqa: BLE001, because we want to handle it
        return get_exception_action_response(
            e=e,
            logger=logger,
            name=update_document_collection_mapping.__name__,
            response=BaseResponse(
                message=f"unable to update_document_collection_mapping with exception: {e}"
            ),
        )
    return STATUS_OK


def create_new_document_collection(
    request: Request,
    request_input: CreateDocumentCollectionModel,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> DocumentCollectionModel:
    __check_rag_document_secret(request)
    try:
        return ragdocument.create_new_document_collection(
            document_collection=request_input
        )
    except Exception as e:  # noqa: BLE001, because we want to handle it
        return get_exception_action_response(
            e=e,
            logger=logger,
            name=create_new_document_collection.__name__,
            response=BaseResponse(
                message=f"unable to create_new_document_collection with exception: {e}"
            ),
        )


def update_document_collection(
    request: Request,
    request_input: DocumentCollectionModel,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> dict:
    __check_rag_document_secret(request)
    try:
        ragdocument.update_document_collection(request_input)

    except Exception as e:  # noqa: BLE001, because we want to handle it.
        return get_exception_action_response(
            e=e,
            logger=logger,
            name=update_document_collection.__name__,
            response=BaseResponse(
                message=f"unable to update_document_collection with exception: {e}"
            ),
        )
    return STATUS_OK


def search_document_knowledge_base(
    request: Request,
    request_input: DocumentKnowledgeBaseRequestModel,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> Dict[str, list[SearchKnowledgeBaseResult]]:
    __check_rag_document_secret(request)
    try:
        return {
            "result": ragdocument.knowledge_base_search(request_input=request_input)
        }
    except Exception as e:  # noqa: BLE001, because we want to handle it
        return get_exception_action_response(
            e=e,
            logger=logger,
            name=search_document_knowledge_base.__name__,
            response=BaseResponse(
                message=f"unable to search_document_knowledge_base with exception: {e}"
            ),
        )


async def file_upload_document_rag_handler(
    files: List[UploadFile],
) -> List[FileMetadata]:
    # check if the uploaded files are valid
    await check_upload_file_req(files)

    # convert file uploaded by user to file metadata
    files_uploaded_by_user: List[
        FileMetadata
    ] = await convert_file_uploaded_to_file_metadata(files)

    return files_uploaded_by_user


async def ingest_new_doc_content_stream_handler(
    request_input: IngestDocumentContentRequest,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> Callable[[None], Generator[str, None, None]]:
    try:
        # declare function for running doc content async request
        def run_async_function_in_thread(loop: AbstractEventLoop) -> str:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                __store_new_document_information(
                    filename=request_input.filename,
                    file_path=request_input.document_uri,
                    document_collection_uuid=request_input.document_collection_uuid,
                    file_content=request_input.document_content,
                    file_type=FILETYPE_FILE_CONTENT,
                    ragdocument=ragdocument,
                )
            )

            return IngestNewDocumentContentResponse(
                document_information=result.__dict__,
                status="OK",
            ).__dict__.__str__()

        loop = asyncio.new_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)

        # define new function for generating streaming response
        def generate_streaming_response() -> Generator[str, None, None]:
            future = executor.submit(run_async_function_in_thread, loop)
            while not future.done():
                time.sleep(1)
                processing_str = IngestNewDocumentContentResponse(
                    status="Processing", document_information={}
                ).__dict__.__str__()
                yield f"{processing_str}\n"
            yield future.result()

        return generate_streaming_response  # noqa: TRY300
    except Exception as e:  # noqa: BLE001 because we want to handle it
        exception = get_exception_action_response(
            e=e,
            logger=logger,
            name=ingest_new_doc_content_stream_handler.__name__,
            response=BaseResponse(
                message=f"unable to call ingest_new_doc_content_stream_handler with exception: {e}"
            ),
        )
        return lambda: str(exception.body)


async def ingest_new_doc_content(
    request: Request,
    request_input: IngestDocumentContentRequest,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> DocumentInformationModel:
    __check_rag_document_secret(request)
    try:
        return __store_new_document_information(
            filename=request_input.filename,
            file_path=request_input.document_uri,
            document_collection_uuid=request_input.document_collection_uuid,
            file_content=request_input.document_content,
            file_type=FILETYPE_FILE_CONTENT,
            ragdocument=ragdocument,
        )

    except Exception as e:  # noqa: BLE001, because we want to handle it
        return get_exception_action_response(
            e=e,
            logger=logger,
            name=ingest_new_doc_content.__name__,
            response=BaseResponse(
                message=f"unable to ingest_new_doc_content with exception: {e}"
            ),
        )


async def ingest_new_doc_invoke_handler(
    request: Request,
    files: List[UploadFile],
    document_collection_uuid: str,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> UploadDocumentResponse | JSONResponse:
    try:
        files_uploaded_by_user = await file_upload_document_rag_handler(files=files)

        ingest_new_doc_data = await ingest_new_doc(
            request=request,
            files=files_uploaded_by_user,
            document_collection_uuid=document_collection_uuid,
            ragdocument=ragdocument,
        )
        return UploadDocumentResponse(
            files=ingest_new_doc_data,
            status="OK",
        )
    except Exception as e:  # noqa: BLE001 because we want to handle it
        return get_exception_action_response(
            e=e,
            logger=logger,
            name=ingest_new_doc_stream_handler.__name__,
            response=BaseResponse(
                message=f"unable to call ingest_new_doc_stream_handler with exception: {e}"
            ),
        )


async def ingest_new_doc_stream_handler(
    request: Request,
    files: List[UploadFile],
    document_collection_uuid: str,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> Callable[[None], Generator[str, None, None]]:
    try:
        files_uploaded_by_user = await file_upload_document_rag_handler(files=files)

        # declare function for running ingest doc async request
        def run_async_function_in_thread(loop: AbstractEventLoop) -> str:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                ingest_new_doc(
                    request=request,
                    files=files_uploaded_by_user,
                    document_collection_uuid=document_collection_uuid,
                    ragdocument=ragdocument,
                ),
            )
            return UploadDocumentResponse(
                files=result,
                status="OK",
            ).__dict__.__str__()

        loop = asyncio.new_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)

        # define new function for generating streaming response
        def generate_streaming_response() -> Generator[str, None, None]:
            future = executor.submit(run_async_function_in_thread, loop)
            while not future.done():
                time.sleep(1)
                processing_str = UploadDocumentResponse(
                    status="Processing", files=[]
                ).__dict__.__str__()
                yield f"{processing_str}\n"
            yield future.result()

        return generate_streaming_response  # noqa: TRY300
    except Exception as e:  # noqa: BLE001 because we want to handle it
        exception = get_exception_action_response(
            e=e,
            logger=logger,
            name=ingest_new_doc_stream_handler.__name__,
            response=BaseResponse(
                message=f"unable to call ingest_new_doc_stream_handler with exception: {e}"
            ),
        )
        return lambda: str(exception.body)


async def ingest_new_doc(
    request: Request,
    files: List[FileMetadata],
    document_collection_uuid: str,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> List[Dict]:
    __check_rag_document_secret(request)

    uploaded_files = await __upload_file_to_s3_handler(files)

    return [
        (
            (
                await __store_new_document_information(
                    filename=uploaded_file.filename,
                    file_path=uploaded_file.file_path,
                    document_collection_uuid=document_collection_uuid,
                    file_content=uploaded_file.file_content,
                    ragdocument=ragdocument,
                )
            ).__dict__
        )
        for uploaded_file in uploaded_files
    ]


def update_document_information(
    request: Request,
    request_input: DocumentInformationRequestModel,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> dict:
    __check_rag_document_secret(request)
    try:
        ragdocument.update_document_information(request_input)

    except Exception as e:  # noqa: BLE001, because we want to handle it
        return get_exception_action_response(
            e=e,
            logger=logger,
            name=update_document_information.__name__,
            response=BaseResponse(
                message=f"unable to update_document_information with exception: {e}"
            ),
        )
    else:
        return STATUS_OK


def get_document_collection_metadata(
    document_collection_uuid: str,
    request: Request,
    ragdocument: RagDocumentClient = Depends(get_ragdocument),
) -> DocumentCollectionMetadata:
    __check_rag_document_secret(request)

    try:
        return ragdocument.get_document_collection_metadata(document_collection_uuid)
    except Exception as e:  # noqa: BLE001, because we want to handle it
        return get_exception_action_response(
            e=e,
            logger=logger,
            name="get_document_collection_metadata",
            response=BaseResponse(
                message=f"unable to get_document_collection_metadata with exception: {e}"
            ),
        )


async def __store_new_document_information(  # noqa: PLR0913
    filename: str,
    file_path: str,
    file_content: str,
    document_collection_uuid: str,
    ragdocument: RagDocumentClient,
    file_type: str = FILETYPE_UPLOAD_FILE,
) -> DocumentInformationModel:
    # insert document information first
    document_information = ragdocument.insert_new_document_information(
        new_document=DocumentInformation(
            filename=filename,
            file_path=file_path,
            file_type=file_type,
        ),
        document_collection_uuid=document_collection_uuid,
    )

    # split and embed file
    splited_texts = ragdocument.text_pre_processing(
        file_content,
    )

    for splited_text in splited_texts:
        # embed text
        embedded_text = ragdocument.embed_query(splited_text)
        document_embedding = DocumentEmbedding(
            token_number=num_tokens_from_string(splited_text),
            embedding=embedded_text,
            document_information_id=document_information.id,
            text_snipplet=splited_text,
        )
        ragdocument.insert_embedding_document(document_embedding)

    return DocumentInformationModel(
        filename=document_information.filename,
        document_last_updated=str(document_information.document_last_updated),
        file_path=document_information.file_path,
        media_serve_file_path=get_media_server_url(
            document_information.file_path, document_information.file_type
        ),
        file_type=document_information.file_type,
        id=document_information.id,
        status=document_information.status,
    )


async def __upload_file_to_s3_handler(files: List[FileMetadata]) -> List[FileMetadata]:
    # create a folder for each request
    request_folder = get_temporary_filename()

    file_metadata_collection = []
    for file in files:
        # get file contents, convert them to io
        file_data = io.BytesIO(file.file_content_byte)

        # construct the file path where we store the file in S3
        file_path = s3_construct_file_path(file.filename, request_folder)

        # upload the file to S3
        s3_upload_file(file_data, file_path)

        file_metadata_collection.append(
            FileMetadata(
                filename=file.filename,
                file_content=get_file_content_from_bytes(
                    file.file_content_byte,
                    filename=file.filename,
                ),
                file_path=file_path,
                file_content_byte=file.file_content_byte,
            )
        )
    return file_metadata_collection


async def convert_file_uploaded_to_file_metadata(
    files: List[UploadFile],
) -> List[FileMetadata]:
    return [
        FileMetadata(
            file_content_byte=await file.read(),
            filename=file.filename,
            file_path="",
            file_content="",
        )
        for file in files
    ]
