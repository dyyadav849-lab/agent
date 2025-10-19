import re
from typing import Dict, List

from app.core.azure_em.client import EmbeddingModelClient
from app.core.log.logger import Logger
from app.core.transformer.client import TransformerClient
from app.models.azure_openai_model import (
    GrabGPTOpenAIModel,
)
from app.routes.doc_kb_route.models import (
    CreateDocumentCollectionModel,
    DocumentCollectionMappingModel,
    DocumentCollectionMetadata,
    DocumentCollectionModel,
    DocumentEmbeddingResponse,
    DocumentInformationModel,
    DocumentInformationRequestModel,
    DocumentKnowledgeBaseRequestModel,
    SearchKnowledgeBaseResult,
)
from app.storage.ragdocument_db.client import RagDocumentDbClient
from app.storage.ragdocument_db.models import (
    DocumentCollection,
    DocumentEmbedding,
    DocumentInformation,
)


class RagDocumentClient:
    """
    RagDocument Client is the entry point class for ragdocument db related operation.
    Please use `.init_embedding_model` if there is model preference, else, embed_query is using default model.

    `Default model`: text-embedding-ada-002
    """

    def __init__(
        self,
        ragdocument_db: RagDocumentDbClient,
        embedding_model: EmbeddingModelClient,
        transformer: TransformerClient,
    ) -> None:
        self.__ragdocument_db = ragdocument_db
        self.__embedding_model = embedding_model
        self.__transformer = transformer
        self.init_embedding_model()
        self.__logger = Logger(name=self.__class__.__name__)

    def init_embedding_model(
        self, model: str = GrabGPTOpenAIModel.ADA_002, timeout: int = 300
    ) -> None:
        """
        Initialize AzureOpenAI embedding model based on model provided. Timeout default = 300
        """
        self.__embedding_model.init(model, timeout)

    def embed_query(self, text: str) -> list[float]:
        """
        Embed query with AzureOpenAIModel
        """
        return self.__embedding_model.embed_query(text)

    def text_pre_processing(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 200,
        splitter_selector: int = 1,
    ) -> list[str]:
        """
        Pre-processing for incoming text into desired chunk
        """
        text = text.lower()

        if chunk_overlap != 0 and chunk_overlap > chunk_size:
            exception_message = "Chunk overlap is larger than chunk size"
            raise Exception(exception_message)

        return self.__transformer.chunk_text(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter_selector=splitter_selector,
        )

    def create_new_document_collection(
        self, document_collection: CreateDocumentCollectionModel
    ) -> DocumentCollectionModel:
        new_document_collection_data = (
            self.__ragdocument_db.create_new_document_collection(
                DocumentCollection(
                    name=document_collection.name,
                    description=document_collection.description,
                )
            )
        )

        return DocumentCollectionModel(
            description=new_document_collection_data.description,
            uuid=new_document_collection_data.uuid,
            name=new_document_collection_data.name,
            status=new_document_collection_data.status,
        )

    def update_document_collection(
        self, document_collection: DocumentCollectionModel
    ) -> None:
        self.__ragdocument_db.update_document_collection_data(
            DocumentCollection(
                uuid=document_collection.uuid,
                name=document_collection.name,
                description=document_collection.description,
                status=document_collection.status,
            )
        )

    def insert_embedding_document(self, embedded_document: DocumentEmbedding) -> None:
        self.__ragdocument_db.insert_embedding_document(
            embedded_document=embedded_document
        )

    def knowledge_base_search(
        self,
        request_input: DocumentKnowledgeBaseRequestModel,
    ) -> list[SearchKnowledgeBaseResult]:
        """
        To perform kb search for slack conversation history based on query.
        """
        query = request_input.query
        if query == "":
            return []

        query = query.lower()
        query = re.sub(r"\n+", "", query)

        embeded_query = self.embed_query(query)

        results = self.__ragdocument_db.read_document_embedding_data(
            embeded_query=embeded_query,
            document_collection_uuids=request_input.filter.document_collection_uuids,
        )

        document_information_ids = [
            result.document_information_id for result in results
        ]

        document_informations = self.__ragdocument_db.get_document_informations_on_ids(
            document_information_ids=document_information_ids
        )
        document_information_map: Dict[int, DocumentInformation] = {}
        for document_information in document_informations:
            document_information_map[document_information.id] = document_information

        search_results: List[SearchKnowledgeBaseResult] = []
        for result in results:
            document_information_pair: DocumentInformation | None = (
                document_information_map.get(result.document_information_id, None)
            )
            if document_information_pair is None:
                continue

            search_results.append(
                SearchKnowledgeBaseResult(
                    document_embedding=DocumentEmbeddingResponse(
                        document_information_id=result.document_information_id,
                        status=result.status,
                        text_snipplet=result.text_snipplet,
                        token_number=result.token_number,
                    ),
                    document_information=DocumentInformationModel(
                        filename=document_information.filename,
                        id=document_information_pair.id,
                        document_last_updated=str(
                            document_information_pair.document_last_updated
                        ),
                        status=document_information_pair.status,
                        file_path=document_information_pair.file_path,
                        file_type=document_information_pair.file_type,
                    ),
                )
            )

        return search_results

    def insert_new_document_information(
        self, new_document: DocumentInformation, document_collection_uuid: str
    ) -> DocumentInformation:
        return self.__ragdocument_db.insert_new_document_information(
            new_document=new_document, document_collection_uuid=document_collection_uuid
        )

    def update_document_information(
        self,
        request_input: DocumentInformationRequestModel,
    ) -> None:
        self.__ragdocument_db.update_document_information(request_input)

    def update_document_collection_mapping(
        self,
        request_input: DocumentCollectionMappingModel,
    ) -> None:
        self.__ragdocument_db.update_document_collection_mapping(request_input)

    def get_document_collection_metadata(
        self, document_collection_uuid: str
    ) -> DocumentCollectionMetadata:
        return self.__ragdocument_db.get_document_collection_metadata(
            document_collection_uuid
        )
