from langchain_text_splitters import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.core.log.logger import Logger
from app.core.transformer.text_splitter.models import TextSplitterEnum


class TextSplitterClient:
    def __init__(self) -> None:
        self.__logger = Logger(name=self.__class__.__name__)

    def split_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int = 0,
        splitter_selector: int = 0,
    ) -> list[str]:
        """
        Match text splitter based on enum
        """
        match TextSplitterEnum(splitter_selector).name:
            case TextSplitterEnum.DEFAULT.name:
                return self.split_text_by_character_text_spliiter(text)
            case TextSplitterEnum.RECURSIVE.name:
                return self.split_text_by_recursive_text_spliiter(
                    text, chunk_size, chunk_overlap
                )
            case _:
                return [text]

    def split_text_by_recursive_text_spliiter(
        self, text: str, chunk_size: int, chunk_overlap: int = 0
    ) -> list[str]:
        try:
            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                encoding_name="cl100k_base",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            return text_splitter.split_text(text)

        except Exception as e:
            log_message = f"TokenTextSplitter Error {e!s}"
            self.__logger.exception(log_message)
            # Raising for tracebility
            raise Exception(log_message) from e

    def split_text_by_character_text_spliiter(self, text: str) -> list[str]:
        """
        Known issue, does not use pass in chunk size and overlap, only using default one.
        issues: https://github.com/langchain-ai/langchain/issues/10410
        """
        try:
            text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
                encoding_name="cl100k_base",
            )

            return text_splitter.split_text(text)

        except Exception as e:
            log_message = f"TokenTextSplitter Error {e!s}"
            self.__logger.exception(log_message)
            # Raising for tracebility
            raise Exception(log_message) from e
