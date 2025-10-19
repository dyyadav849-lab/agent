import re
from typing import Dict, Optional, Tuple

from fastapi.encoders import jsonable_encoder

from app.core.azure_em.client import EmbeddingModelClient
from app.core.log.logger import Logger
from app.core.transformer.client import TransformerClient
from app.models.utils import num_tokens_from_string
from app.routes.slack_kb_route.models import (
    InsertRequestModel,
    KnowledgeBaseRequestModel,
    Pagination,
)
from app.storage.ragslack_db.client import RagSlackDbClient
from app.storage.ragslack_db.models import (
    QueriesToSlackEmbeddingsRecords,
    QueriesToSlackInformationMapping,
    SlackMessageEmbeddingDoc,
    SlackMessageInformationDoc,
)


class RagSlackClient:
    """
    Ragslack Client is the entry point class for ragslack db related operation.
    Please use `.init_embedding_model` if there is model preference, else, embed_query is using default model.

    `Default model`: text-embedding-ada-002
    """

    def __init__(
        self,
        ragslack_db: RagSlackDbClient,
        embedding_model: EmbeddingModelClient,
        transformer: TransformerClient,
    ) -> None:
        self.__ragslack_db = ragslack_db
        self.__embedding_model = embedding_model
        self.__transformer = transformer
        self.__logger = Logger(name=self.__class__.__name__)

    def init_embedding_model(self, model: str, timeout: int = 300) -> None:
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
        chunk_size: int = 0,
        chunk_overlap: int = 0,
        splitter_selector: int = 0,
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

    def knowledge_base_search(
        self, request_input: KnowledgeBaseRequestModel, embedding_operator: str
    ) -> list[SlackMessageEmbeddingDoc]:
        """
        To perform kb search for slack conversation history based on query.
        """
        query = request_input.query
        if query == "":
            return []

        query = query.lower()
        query = re.sub(r"\n+", "", query)

        embeded_query = self.embed_query(query)

        result = self.__ragslack_db.read_slack_embedding_data(
            embeded_query,
            embedding_operator,
            request_input.vector_threshold,
        )

        query_record = QueriesToSlackEmbeddingsRecords(
            query_summary=query, num_of_embedding_found=len(result)
        )

        self.__ragslack_db.insert_query_to_embedding_records(query_record)

        if len(result) == 0:
            return result

        query_to_slack_mapping_docs: list[QueriesToSlackInformationMapping] = []

        for data in result:
            computed_dot_product = self.__transformer.compute_inner_product_similarity(
                embeded_query, data.embedding
            )

            query_mapping = QueriesToSlackInformationMapping(
                slack_message_information_id=data.slack_message_information_id,
                queries_to_slack_embeddings_records_id=query_record.id,
                dot_product_score=computed_dot_product,
            )

            query_to_slack_mapping_docs.append(query_mapping)

            if len(query_to_slack_mapping_docs) == 5:  # noqa: PLR2004: replace 5 with constant variable
                break

        self.__ragslack_db.insert_query_to_slack_mappings(query_to_slack_mapping_docs)

        return result

    def read_slack_information(
        self,
        knowledge_base_result: list[SlackMessageEmbeddingDoc],
        limit: int,
        page: int,
        filter_list: Optional[Dict[str, list[str]]] = None,
    ) -> Tuple[list[SlackMessageInformationDoc], Pagination]:
        """
        To read slack message information from db, e.g. channel id, messageTs etc.
        """
        ids = [
            result.slack_message_information_id
            for result in knowledge_base_result
            if result.slack_message_information_id is not None
        ]

        filtered_ids, pagination = self.__transformer.filter_query_ids_by_page(
            ids, page, limit
        )

        if len(ids) == 0:
            return [], Pagination()

        return self.__ragslack_db.read_slack_information_by_id(
            filtered_ids, filter_list
        ), pagination

    def insert_slack_information_to_db(
        self, input_request: InsertRequestModel
    ) -> SlackMessageInformationDoc:
        """
        Insert slack information data to ragslack_db.
        """
        slack_information_doc = SlackMessageInformationDoc(
            channel_id=input_request.channel_id,
            main_thread_ts=input_request.main_thread_ts,
            chat_summary=input_request.chat_summary,
            chat_history=jsonable_encoder(input_request.chat_history),
            is_embedded=False,
        )
        return self.__ragslack_db.insert_slack_information_data(slack_information_doc)

    def insert_embeded_to_db(
        self, text_list: list[str], slack_information_doc: SlackMessageInformationDoc
    ) -> None:
        """
        Insert embedded data to ragslack_db, skip if text_list not provided
        """
        try:
            channel_id = slack_information_doc.channel_id
            message_ts = slack_information_doc.main_thread_ts
            if len(text_list) == 0:
                error_message = "No text summary is provided"
                raise Exception(error_message)

            existing_doc = (
                self.__ragslack_db.read_embedded_by_slack_information_channel_id(
                    [slack_information_doc.id]
                )
            )

            if len(existing_doc) != 0:
                self.__ragslack_db.delete_embedded_data(
                    existing_doc[0].slack_message_information_id
                )
                self.logging_info("Deleted previous embed data", channel_id, message_ts)

            slack_message_embedding_docs: list[SlackMessageEmbeddingDoc] = []

            for text in text_list:
                text_to_insert = text.strip()

                if len(text_to_insert) == 0:
                    continue

                slack_message_embedding_docs.append(
                    SlackMessageEmbeddingDoc(
                        token_number=num_tokens_from_string(text_to_insert),
                        embedding=self.embed_query(text_to_insert),
                        slack_message_information_id=slack_information_doc.id,
                    )
                )

            self.__ragslack_db.insert_embedding_data(slack_message_embedding_docs)
            self.logging_info("Insert embed data successfully", channel_id, message_ts)
            slack_information_doc.is_embedded = True
            self.__ragslack_db.update_slack_information_data(slack_information_doc)
            self.logging_info(
                "Update slack information data successfully", channel_id, message_ts
            )

        except Exception as e:
            log_message = f"Error: {e!s}"
            self.__logger.exception(log_message)
            error_message = "Unable to insert embed data to pgvectordb"
            raise Exception(error_message) from e

    def logging_info(self, message: str, channel_id: str, message_ts: str) -> None:
        info_message = f"{message},id: {channel_id} | messagea_ts: {message_ts}"
        self.__logger.info(info_message)

    def get_slack_messages(
        self,
        filter_conditions: list[Dict[str, list[str]]],
        limit: int = 100,
        offset: int = 0
    ) -> list[SlackMessageInformationDoc]:
        """Get slack messages with optional filtering"""
        try:
            return self.__ragslack_db.get_slack_messages(
                filter_conditions=filter_conditions,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            self.__logger.error(f"Failed to get slack messages: {e}")
            raise

    def get_slack_messages_count(
        self,
        filter_conditions: list[Dict[str, list[str]]]
    ) -> int:
        """Get total count of slack messages matching filter conditions"""
        try:
            return self.__ragslack_db.get_slack_messages_count(filter_conditions)
        except Exception as e:
            self.__logger.error(f"Failed to get slack messages count: {e}")
            raise
