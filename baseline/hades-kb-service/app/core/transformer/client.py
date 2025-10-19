import math
from typing import Tuple

import numpy as np

from app.core.constant import query_limit
from app.core.log.logger import Logger
from app.core.transformer.text_splitter.client import TextSplitterClient
from app.models.utils import num_tokens_from_string
from app.routes.slack_kb_route.models import Pagination


class TransformerClient:
    def __init__(self, text_splitter: TextSplitterClient) -> None:
        """
        Master class for transformation
        """
        self.__text_splitter = text_splitter
        self.__logger = Logger(name=self.__class__.__name__)
        self.__grab_workspace = "grab"

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 0,
        chunk_overlap: int = 0,
        splitter_selector: int = 0,
    ) -> list[str]:
        """
        Chunking strategies references: https://www.pinecone.io/learn/chunking-strategies/
        Default setting:
        `chunk_size`: 512
        `chunk_overlap`:200
        """
        try:
            if chunk_size <= 0:
                chunk_size = 512

            if chunk_overlap <= 0:
                chunk_overlap = 200

            token_size = num_tokens_from_string(text)

            if token_size < chunk_size:
                return [text]

            return self.__text_splitter.split_text(
                text, chunk_size, chunk_overlap, splitter_selector
            )

        except Exception as e:
            log_message = f"Text chunking Error: {e!s}"
            self.__logger.exception(log_message)
            return [text]

    def compute_inner_product_similarity(
        self, query_vector: list[float], result_vector: list[float]
    ) -> float:
        try:
            query_vector_np = np.array(query_vector)
            result_vector_np = np.array(result_vector)
            return float(np.dot(query_vector_np, result_vector_np))
        except Exception as e:
            log_message = f"Inner product calculation Error: {e!s}"
            self.__logger.exception(log_message)
            return 0

    def generate_slack_url(self, channel_id: str, mainthread_timestamp: str) -> str:
        base_url = f"https://{self.__grab_workspace}.slack.com/archives/{channel_id}/p"

        try:
            mainthread_timestamp_float = float(mainthread_timestamp)
            slack_timestamp = int(mainthread_timestamp_float * 1000000)

        except (ValueError, TypeError):
            log_message = f"timestamp is not numerical: {mainthread_timestamp}"
            self.__logger.exception(log_message)
            slack_timestamp = mainthread_timestamp

        return f"{base_url}{slack_timestamp}"

    def filter_query_ids_by_page(
        self, ids: list[int], page: int = 1, page_size: int = query_limit
    ) -> Tuple[list[int], Pagination]:
        try:
            if len(ids) == 0:
                return ids, Pagination()

            total_page = math.ceil(len(ids) / page_size)
            if page > total_page:
                page = 1

            start_index = (page - 1) * page_size
            end_index = min(start_index + page_size, len(ids))
            filtered_ids = ids[start_index:end_index]

            return filtered_ids, Pagination(
                total_page=total_page,
                page_size=page_size,
                current_page=page,
                total_items_count=len(ids),
            )

        except Exception as e:
            log_message = f"Unable to compute page {e!s}"
            self.__logger.exception(log_message)
            error_message = "Compute page error"
            raise Exception(error_message) from e
