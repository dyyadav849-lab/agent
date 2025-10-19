import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List

from sqlalchemy import Float, and_, select
from sqlalchemy.orm import Session

from app.core.log.logger import Logger
from app.core.s3.bucket_util import get_media_server_url
from app.routes.doc_kb_route.models import (
    DocumentCollectionMappingMetadata,
    DocumentCollectionMappingModel,
    DocumentCollectionMetadata,
    DocumentCollectionModel,
    DocumentInformationModel,
    DocumentInformationRequestModel,
)
from app.storage.ragdocument_db.constant import ACTIVE_STATUS, INACTIVE_STATUS
from app.storage.ragdocument_db.models import (
    DocumentCollection,
    DocumentCollectionMapping,
    DocumentEmbedding,
    DocumentInformation,
)


class RagDocumentDbClient:
    def __init__(self, db_session: Callable[..., Session]) -> None:
        self.__db_session = db_session
        self.__logger = Logger(name=self.__class__.__name__)

    # create new document collection
    def create_new_document_collection(
        self, document_collection: DocumentCollection
    ) -> DocumentCollection:
        """
        Method to create a new document collection.
        """

        # create uuid for a document collection
        document_collection.uuid = (
            f"{uuid.uuid4()!s}_{int(round(time.time() * 1000))!s}"
        )
        try:
            with self.__db_session() as session:
                session.add(document_collection)
                session.commit()

                # get the new document collection inserted ID
                session.refresh(document_collection)

                return document_collection

        except Exception as e:
            description = "insert new document collection failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            raise Exception(log_message) from e

    def update_document_collection_data(self, document: DocumentCollection) -> None:
        """
        Method to update document collection data.
        """
        try:
            with self.__db_session() as session:
                # search to see if the document collection already exists
                document_collection_db = (
                    session.query(DocumentCollection)
                    .filter(
                        DocumentCollection.uuid == document.uuid,
                    )
                    .first()
                )

                if document_collection_db is None:
                    error_message = (
                        "document collection with uuid: {document.uuid} does not exist"
                    )
                    raise ValueError(error_message)

                document_collection_db.description = document.description
                document_collection_db.name = document.name
                document_collection_db.status = document.status

                session.merge(document_collection_db)
                session.commit()

        except Exception as e:
            description = "update document collection failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            raise Exception(log_message) from e

    def update_document_information(
        self, request_input: DocumentInformationRequestModel
    ) -> None:
        """
        Method to update document information
        """
        try:
            with self.__db_session() as session:
                document_information = (
                    session.query(DocumentInformation)
                    .filter(
                        DocumentInformation.id == request_input.id,
                    )
                    .first()
                )

                if document_information is None:
                    error_message = f"document information id provided: {request_input.id} does not exist in database"
                    raise ValueError(error_message)

                document_information.status = request_input.status

                session.merge(document_information)
                session.commit()
        except Exception as e:
            description = "Update document information data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            raise Exception(log_message) from e

    def insert_embedding_document(self, embedded_document: DocumentEmbedding) -> None:
        """
        Method to insert document embeddings
        """

        try:
            with self.__db_session() as session:
                session.add(embedded_document)
                session.commit()
        except Exception as e:
            description = "Insert document embedding data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)

            raise Exception(log_message) from e

    def update_document_collection_mapping(
        self, document_collection_mapping: DocumentCollectionMappingModel
    ) -> None:
        """
        Method to update document collection mapping data
        """

        try:
            with self.__db_session() as session:
                document_collection_mapping_db = (
                    session.query(DocumentCollectionMapping)
                    .filter(
                        and_(
                            DocumentCollectionMapping.document_collection_uuid
                            == document_collection_mapping.document_collection_uuid,
                            DocumentCollectionMapping.document_information_id
                            == document_collection_mapping.document_information_id,
                        )
                    )
                    .first()
                )
                if document_collection_mapping_db is None:
                    error_message = f"unable to find document collection mapping for document_collection_uuid: {document_collection_mapping.document_collection_uuid} and document_information_id: {document_collection_mapping.document_information_id}"
                    raise ValueError(error_message)
                document_collection_mapping_db.status = (
                    document_collection_mapping.status
                )
                session.merge(document_collection_mapping_db)
                session.commit()
        except Exception as e:
            description = "Update document collection data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)

            raise Exception(log_message) from e

    def read_document_embedding_data(
        self,
        embeded_query: List[float],
        document_collection_uuids: List[str],
        embedding_operator: str = "<#>",
        vector_threshold: float = 0.7,
    ) -> list[DocumentEmbedding]:
        """
        Method to read document embedding data based on operator and limit.
        Important: multiply with -1 if computing with inner product at pgvector. Due to how pgvector computing negative inner product.

        """
        try:
            if len(embeded_query) == 0:
                return []

            with self.__db_session() as session:
                document_collections = session.query(DocumentCollection).filter(
                    and_(
                        DocumentCollection.uuid.in_(document_collection_uuids),
                        DocumentCollection.status == ACTIVE_STATUS,
                    )
                )

                if document_collections is None or document_collections.count() == 0:
                    # the document collection might be disabled
                    return []

                document_collection_mappings = session.query(
                    DocumentCollectionMapping
                ).filter(
                    and_(
                        DocumentCollectionMapping.document_collection_uuid.in_(
                            document_collection_uuids
                        ),
                        DocumentCollectionMapping.status == ACTIVE_STATUS,
                    )
                )

                if (
                    document_collection_mappings is None
                    or document_collection_mappings.count() == 0
                ):
                    # the document collection id provided has no document inside it
                    return []

                document_information_ids = [
                    document_collection_mapping.document_information_id
                    for document_collection_mapping in document_collection_mappings
                ]

                # search for the documents that are still active
                document_informations_active = session.query(
                    DocumentInformation
                ).filter(
                    and_(
                        DocumentInformation.status == ACTIVE_STATUS,
                        DocumentInformation.id.in_(document_information_ids),
                    )
                )

                if (
                    document_informations_active is None
                    or document_informations_active.count() == 0
                ):
                    return []

                document_information_ids = [
                    document_information_active.id
                    for document_information_active in document_informations_active
                ]

                base_clause_statement = DocumentEmbedding.embedding.op(
                    embedding_operator, return_type=Float
                )(embeded_query)

                clause_statement = base_clause_statement.desc()

                if embedding_operator == "<#>":
                    clause_statement = -1 * clause_statement
                    base_clause_statement = -1 * base_clause_statement

                statement = (
                    select(DocumentEmbedding)
                    .order_by(clause_statement)
                    .filter(
                        and_(
                            DocumentEmbedding.status == ACTIVE_STATUS,
                            DocumentEmbedding.document_information_id.in_(
                                document_information_ids
                            ),
                            base_clause_statement > vector_threshold,
                        )
                    )
                )

                result = session.scalars(statement).all()

                if result is None:
                    return []

                return result

        except Exception as e:
            description = "Read document embedding data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            raise Exception(log_message) from e

    def get_document_informations_on_ids(
        self, document_information_ids: List[int]
    ) -> List[DocumentInformation]:
        try:
            with self.__db_session() as session:
                return session.query(DocumentInformation).filter(
                    DocumentInformation.id.in_(document_information_ids)
                )

        except Exception as e:
            description = "Get document information data based on id failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)

            raise Exception(log_message) from e

    def insert_new_document_information(
        self, new_document: DocumentInformation, document_collection_uuid: str
    ) -> DocumentInformation:
        try:
            existing_doc_id = 0
            with self.__db_session() as session:
                existing_doc = (
                    session.query(DocumentInformation)
                    .filter(
                        DocumentInformation.file_path == new_document.file_path,
                    )
                    .first()
                )

                if existing_doc is None:
                    # insert the new document
                    session.add(new_document)

                    existing_doc = new_document
                else:
                    # get all the document embeddings that are linked to the current document, set them as inactive
                    existing_doc_embeddings = session.query(DocumentEmbedding).filter(
                        DocumentEmbedding.document_information_id == existing_doc.id,
                    )
                    if existing_doc_embeddings is not None:
                        for existing_doc_embedding in existing_doc_embeddings:
                            existing_doc_embedding.status = INACTIVE_STATUS
                            session.merge(existing_doc_embedding)
                            session.commit()

                    # update the document information
                    existing_doc.document_last_updated = datetime.now(timezone.utc)
                    session.merge(existing_doc)

                session.commit()
                existing_doc_id = existing_doc.id

            with self.__db_session() as session:
                # check if the document is being added to the document collection already
                existing_doc_collection_mapping = (
                    session.query(DocumentCollectionMapping)
                    .filter(
                        and_(
                            DocumentCollectionMapping.document_collection_uuid
                            == document_collection_uuid,
                            DocumentCollectionMapping.document_information_id
                            == existing_doc_id,
                        )
                    )
                    .first()
                )

                if existing_doc_collection_mapping is None:
                    # insert the new document
                    session.add(
                        DocumentCollectionMapping(
                            document_information_id=existing_doc_id,
                            document_collection_uuid=document_collection_uuid,
                        )
                    )

                    session.commit()
                elif (
                    existing_doc_collection_mapping.status == INACTIVE_STATUS
                ):  # mapping exists and is inactive
                    existing_doc_collection_mapping.status = ACTIVE_STATUS
                    session.merge(existing_doc_collection_mapping)
                    session.commit()

                return existing_doc

        except Exception as e:
            description = "Insert document information data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            raise Exception(log_message) from e

    def get_document_collection_metadata(
        self, document_collection_uuid: str
    ) -> DocumentCollectionMetadata:
        try:
            with self.__db_session() as session:
                document_collection = (
                    session.query(DocumentCollection)
                    .filter(
                        DocumentCollection.uuid == document_collection_uuid,
                    )
                    .first()
                )

                if document_collection is None:
                    error_message = f"unable to find document collection for given uuid: {document_collection_uuid}"
                    raise ValueError(error_message)

                document_collection_metadata = DocumentCollectionModel(
                    description=document_collection.description,
                    name=document_collection.name,
                    status=document_collection.status,
                    uuid=document_collection.uuid,
                )

                document_collection_mappings = session.query(
                    DocumentCollectionMapping
                ).filter(
                    DocumentCollectionMapping.document_collection_uuid
                    == document_collection_uuid
                )

                if (
                    document_collection_mappings is None
                    or document_collection_mappings.count() == 0
                ):
                    return DocumentCollectionMetadata(
                        document_collection_metadata=document_collection_metadata,
                        document_informations=[],
                    )

                # store in a hashmap all the document collection id, along with the status of the document collection mapping
                document_collection_mapping_status: Dict[int, str] = {}
                for document_collection_mapping in document_collection_mappings:
                    document_collection_mapping_status[
                        document_collection_mapping.document_information_id
                    ] = document_collection_mapping.status

                document_information_ids = [
                    document_collection_map_index.document_information_id
                    for document_collection_map_index in document_collection_mappings
                ]

                document_informations = session.query(DocumentInformation).filter(
                    DocumentInformation.id.in_(document_information_ids)
                )

                document_information_metadata: List[DocumentInformationModel] = [
                    DocumentCollectionMappingMetadata(
                        status=document_collection_mapping_status.get(
                            document_information.id, ACTIVE_STATUS
                        ),
                        document_information=DocumentInformationModel(
                            id=document_information.id,
                            document_last_updated=str(
                                document_information.document_last_updated
                            ),
                            file_path=document_information.file_path,
                            file_type=document_information.file_type,
                            filename=document_information.filename,
                            media_serve_file_path=get_media_server_url(
                                document_information.file_path,
                                document_information.file_type,
                            ),
                            status=document_information.status,
                        ),
                    )
                    for document_information in document_informations
                ]

                return DocumentCollectionMetadata(
                    document_collection_metadata=document_collection_metadata,
                    document_informations=document_information_metadata,
                )

        except Exception as e:
            description = "Get document collection metadata failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            raise Exception(log_message) from e
