from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import Float, and_, case, delete, desc, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.core.log.logger import Logger
from app.storage.ragslack_db.models import (
    QueriesToSlackEmbeddingsRecords,
    QueriesToSlackInformationMapping,
    SlackMessageEmbeddingDoc,
    SlackMessageInformationDoc,
)


class RagSlackDbClient:
    def __init__(self, db_session: Callable[..., Session]) -> None:
        self.__db_session = db_session
        self.__logger = Logger(name=self.__class__.__name__)

    # insert data and multiple data might can createa a base class
    def insert_slack_information_data(
        self, document: SlackMessageInformationDoc
    ) -> SlackMessageInformationDoc:
        """
        Method to insert single data, no duplicate into table/schema.
        """
        is_update = False
        try:
            with self.__db_session() as session:
                existing_doc = (
                    session.query(SlackMessageInformationDoc)
                    .filter(
                        SlackMessageInformationDoc.channel_id == document.channel_id,
                        SlackMessageInformationDoc.main_thread_ts
                        == document.main_thread_ts,
                    )
                    .first()
                )

                if existing_doc is None:
                    session.add(document)
                else:
                    if existing_doc.chat_summary == document.chat_summary:
                        return existing_doc
                    is_update = True
                    existing_doc.chat_summary = document.chat_summary
                    existing_doc.chat_history = document.chat_history
                    existing_doc.is_embedded = False
                    session.merge(existing_doc)

                session.commit()
                if not is_update:
                    session.refresh(document)
                    return document

                session.refresh(existing_doc)
                return existing_doc

        except Exception as e:
            description = "insert slack information failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            error_message = "Insert slack information data failed"
            raise Exception(error_message) from e

    def update_slack_information_data(
        self, document: SlackMessageInformationDoc
    ) -> None:
        """
        Method to update slack information data.
        """
        try:
            with self.__db_session() as session:
                session.merge(document)
                session.commit()

        except Exception as e:
            description = "update slack information failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            error_message = "update slack information data failed"
            raise Exception(error_message) from e

    def insert_embedding_data(self, embedded_queries: list[Any]) -> None:
        """
        Method to insert bulk data into table/schema, input is a list.
        """
        # Need to prevent duplicate too
        try:
            if len(embedded_queries) == 0:
                return

            with self.__db_session() as session:
                for embedding in embedded_queries:
                    session.add(embedding)
                session.commit()
        except Exception as e:
            description = "Insert emedding data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            error_message = "Insert embeded data failed"
            raise Exception(error_message) from e

    def read_slack_embedding_data(
        self,
        embeded_query: list[float],
        embedding_operator: str,
        vector_threshold: float = 0.7,
    ) -> list[SlackMessageEmbeddingDoc]:
        """
        Method to read embedding data based on operator and limit.
        Important: multiply with -1 if computing with inner product at pgvector. Due to how pgvector computing negative inner product.

        """
        try:
            if len(embeded_query) == 0:
                return []

            with self.__db_session() as session:
                base_clause_statement = SlackMessageEmbeddingDoc.embedding.op(
                    embedding_operator, return_type=Float
                )(embeded_query)

                clause_statement = base_clause_statement.desc()

                if embedding_operator == "<#>":
                    clause_statement = -1 * clause_statement
                    base_clause_statement = -1 * base_clause_statement

                statement = select(SlackMessageEmbeddingDoc).order_by(clause_statement)

                if vector_threshold != 0:
                    statement = statement.filter(
                        base_clause_statement > vector_threshold
                    )

                result = session.scalars(statement).all()

                if result is None:
                    return []

                return self.filter_slack_embedding_data(result)

        except Exception as e:
            description = "Read slack embedding data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            error_message = "Read embedded data failed"
            raise Exception(error_message) from e

    def filter_slack_embedding_data(
        self,
        result_list: list[SlackMessageEmbeddingDoc],
    ) -> list[SlackMessageEmbeddingDoc]:
        filtered_result = []

        if len(result_list) == 0:
            return []

        seens_embedding = set()

        for embedded_info in result_list:
            tracker_id = embedded_info.slack_message_information_id
            if tracker_id not in seens_embedding:
                seens_embedding.add(tracker_id)
                filtered_result.append(embedded_info)

        return filtered_result

    def read_slack_information_by_id(
        self, ids: list[int], filter_list: Optional[Dict[str, list[str]]] = None
    ) -> list[SlackMessageInformationDoc] | None:
        """
        Method to bulk read slack information based on id.
        order condition to ensure the response from db is according to order in IN clause
        """
        try:
            if len(ids) == 0:
                return []

            with self.__db_session() as session:
                clause_statement_list = [SlackMessageInformationDoc.id.in_(ids)]
                query_statement = session.query(SlackMessageInformationDoc)

                if filter_list is not None:
                    for key, value in filter_list.items():
                        if len(value) > 0:
                            slack_information_table_attr: InstrumentedAttribute = (
                                getattr(SlackMessageInformationDoc, key)
                            )
                            clause_statement_list.append(
                                slack_information_table_attr.in_(value)
                            )
                order_conditions = case(
                    {value: index for index, value in enumerate(ids)},
                    value=SlackMessageInformationDoc.id,
                )
                return (
                    query_statement.filter(and_(*clause_statement_list))
                    .order_by(order_conditions)
                    .all()
                )

        except Exception as e:
            description = "Read slack information by id failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            error_message = "Read slack infromation data by id failed"
            raise Exception(error_message) from e

    def read_embedded_by_slack_information_channel_id(
        self, ids: list[int]
    ) -> list[SlackMessageEmbeddingDoc] | None:
        """
        Method to bulk read slack information based on channel_ts-_id.
        """
        try:
            if len(ids) == 0:
                return []

            with self.__db_session() as session:
                return (
                    session.query(SlackMessageEmbeddingDoc)
                    .filter(
                        SlackMessageEmbeddingDoc.slack_message_information_id.in_(ids)
                    )
                    .all()
                )

        except Exception as e:
            description = "Read slack embedded data by slack information id failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            error_message = "Insert embedding data by slack information id failed"
            raise Exception(error_message) from e

    def delete_embedded_data(self, unique_id: int) -> None:
        """
        Method to delete embeded data in slack_embedding_table
        """
        try:
            with self.__db_session() as session:
                session.execute(
                    delete(SlackMessageEmbeddingDoc).where(
                        SlackMessageEmbeddingDoc.slack_message_information_id
                        == unique_id
                    )
                )
                session.commit()

        except Exception as e:
            description = "Delete embedded data failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            error_message = "Delete embedded data failed"
            raise Exception(error_message) from e

    def insert_query_to_embedding_records(
        self, query_record: QueriesToSlackEmbeddingsRecords
    ) -> None:
        """
        Method to insert query record related to slack embeddings data
        """
        try:
            with self.__db_session() as session:
                session.add(query_record)
                session.commit()
                session.refresh(query_record)
                return

        except Exception as e:
            description = "Insert query data for record failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            return

    def insert_query_to_slack_mappings(
        self, queries_to_slack_mapping_docs: list[QueriesToSlackInformationMapping]
    ) -> None:
        """
        Method to insert query to slack records mapping.
        """
        try:
            with self.__db_session() as session:
                if len(queries_to_slack_mapping_docs) == 0:
                    return

                for record in queries_to_slack_mapping_docs:
                    session.add(record)

                session.commit()

        except Exception as e:
            description = "Insert query mapping failed"
            log_message = f"Description: {description} |Error: {e!s}"
            self.__logger.exception(log_message)
            return

    @classmethod
    def check_invalid_slack_filter_key(cls, filter_dict: dict) -> list[str]:
        return [
            key for key in filter_dict if not hasattr(SlackMessageInformationDoc, key)
        ]

    def get_slack_messages(
        self,
        filter_conditions: List[Dict[str, List[str]]],
        limit: int = 100,
        offset: int = 0
    ) -> List[SlackMessageInformationDoc]:
        """Get slack messages with optional filtering"""
        try:
            self.__logger.info(f"Getting slack messages with filter conditions: {filter_conditions}")

            with self.__db_session() as session:
                # Build base query
                query = select(SlackMessageInformationDoc)

                # Add filter conditions
                if filter_conditions:
                    conditions = []
                    for filter_dict in filter_conditions:
                        for key, values in filter_dict.items():
                            if values:
                                column = getattr(SlackMessageInformationDoc, key)
                                if key == "channel_id":
                                    self.__logger.info(f"Adding filter condition: {key} in {values}")
                                    conditions.append(column.in_(values))

                    # Add 24-hour filter
                    conditions.append(SlackMessageInformationDoc.created_at >= text("NOW() - INTERVAL '1 DAY'"))

                    if conditions:
                        query = query.filter(and_(*conditions))

                # Add ordering and pagination
                query = query.order_by(desc(SlackMessageInformationDoc.created_at))
                query = query.limit(limit).offset(offset)

                # Log the final query
                self.__logger.info(f"Executing query: {query}")

                # Execute query
                result = session.scalars(query).all()
                self.__logger.info(f"Query returned {len(result) if result else 0} results")

                # If no results, let's check if the channel exists at all
                if not result and any("channel_id" in d for d in filter_conditions):
                    channel_id = next(d["channel_id"][0] for d in filter_conditions if "channel_id" in d)
                    channel_check = session.query(SlackMessageInformationDoc).filter(
                        SlackMessageInformationDoc.channel_id == channel_id
                    ).first()
                    self.__logger.info(f"Channel {channel_id} exists in database: {channel_check is not None}")

                return result if result else []

        except Exception as e:
            self.__logger.error(f"Failed to get slack messages: {e}")
            raise

    def get_slack_messages_count(
        self,
        filter_conditions: List[Dict[str, List[str]]]
    ) -> int:
        """Get total count of slack messages matching filter conditions"""
        try:
            with self.__db_session() as session:
                # Build base query
                query = select(func.count()).select_from(SlackMessageInformationDoc)

                # Add filter conditions
                if filter_conditions:
                    conditions = []
                    for filter_dict in filter_conditions:
                        for key, values in filter_dict.items():
                            if values:
                                column = getattr(SlackMessageInformationDoc, key)
                                if key == "channel_id":
                                    conditions.append(column.in_(values))

                    # Add 24-hour filter
                    conditions.append(SlackMessageInformationDoc.created_at >= text("NOW() - INTERVAL '1 DAY'"))

                    if conditions:
                        query = query.filter(and_(*conditions))

                # Execute query
                return session.scalar(query) or 0

        except Exception as e:
            self.__logger.error(f"Failed to get slack messages count: {e}")
            raise
