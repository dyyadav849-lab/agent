from app.core.log.logger import Logger
from app.models.azure_openai_model import (
    GrabGPTOpenAIModel,
    get_azure_openai_embeddings_model,
)


class EmbeddingModelClient:
    """
    Class wrapper for azure openai embedding model
    """

    def __init__(self) -> None:
        self.__logger = Logger(name=self.__class__.__name__)

    def init(self, model: str, timeout: int = 300) -> None:
        """
        Manual Trigger to initialize model client
        """
        self.__model = get_azure_openai_embeddings_model(
            model_name=model, timeout=timeout
        )

    def check_model_attribute(self) -> bool:
        """
        Strictly prohibited to change the attribute name
        """
        return hasattr(self, "_EmbeddingModelClient__model")

    def embed_query(self, text: str) -> list[float]:
        """
        Use Default embedding model if not initialize (text-embedding-ada-002)
        """

        try:
            if not self.check_model_attribute():
                self.__model = get_azure_openai_embeddings_model(
                    model_name=GrabGPTOpenAIModel.ADA_002
                )
            return self.__model.embed_query(text)

        except Exception as e:
            log_message = " ".join(["Error:", str(e)])
            self.__logger.exception(log_message)
            error_message = "Unable to embed with azure_open_ai_model"
            raise Exception(error_message) from e
