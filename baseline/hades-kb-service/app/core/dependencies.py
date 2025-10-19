from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.azure_em.client import EmbeddingModelClient
from app.core.ragdocument.client import RagDocumentClient
from app.core.ragslack.client import RagSlackClient
from app.core.transformer.client import TransformerClient
from app.core.transformer.text_splitter.client import TextSplitterClient
from app.storage.connection import get_session
from app.storage.ragdocument_db.client import RagDocumentDbClient
from app.storage.ragslack_db.client import RagSlackDbClient

# Singleton
text_splitter_client = TextSplitterClient()
transformer_client = TransformerClient(text_splitter=text_splitter_client)


# Scoped
def get_db_session() -> Session:
    return get_session()


def get_ragslack_db_session() -> RagSlackDbClient:
    return RagSlackDbClient(db_session=get_db_session)


def get_ragdocument_db_session() -> RagDocumentDbClient:
    return RagDocumentDbClient(db_session=get_db_session)


def get_embedding_model() -> EmbeddingModelClient:
    return EmbeddingModelClient()


def get_transformer_singleton() -> TransformerClient:
    return transformer_client


def get_ragslack(
    ragslack_db: RagSlackDbClient = Depends(get_ragslack_db_session),
    embedding_model: EmbeddingModelClient = Depends(get_embedding_model),
    transformer: TransformerClient = Depends(get_transformer_singleton),
) -> RagSlackClient:
    return RagSlackClient(
        ragslack_db=ragslack_db,
        embedding_model=embedding_model,
        transformer=transformer,
    )


def get_ragdocument(
    ragdocument_db: get_ragdocument_db_session = Depends(get_ragdocument_db_session),
    embedding_model: EmbeddingModelClient = Depends(get_embedding_model),
    transformer: TransformerClient = Depends(get_transformer_singleton),
) -> RagDocumentClient:
    return RagDocumentClient(
        ragdocument_db=ragdocument_db,
        embedding_model=embedding_model,
        transformer=transformer,
    )
