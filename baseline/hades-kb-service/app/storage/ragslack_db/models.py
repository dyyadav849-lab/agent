from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SlackMessageEmbeddingDoc(Base):
    __tablename__ = "slack_message_embedding"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    token_number = Column(BigInteger, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    slack_message_information_id = Column(
        BigInteger, ForeignKey("slack_message_information.id")
    )
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"""<SlackMessageEmbeddingDoc(embedding='{self.embedding}',
        token_number='{self.token_number}'
        slack_message_information_id='{self.slack_message_information_id}'>"""


class SlackMessageInformationDoc(Base):
    __tablename__ = "slack_message_information"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    channel_id = Column(String, nullable=False)
    main_thread_ts = Column(String, nullable=False)
    is_embedded = Column(Boolean, default=False)
    chat_summary = Column(Text, nullable=False)
    chat_history = Column(JSON)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("channel_id", "main_thread_ts", name="uk_channel_ts_id"),
    )

    def __repr__(self) -> str:
        return f"""<SlackMessageInformationDoc(channel_id='{self.channel_id}',
        main_thread_ts='{self.main_thread_ts}',
        chat_summary='{self.chat_summary}',
        chat_history='{self.chat_history}',)>"""


class QueriesToSlackEmbeddingsRecords(Base):
    __tablename__ = "queries_to_slack_embeddings_records"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    query_summary = Column(Text, nullable=False)
    num_of_embedding_found = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"""<QueriesToSlackEmbedding(query_summary='{self.query_summary})>"""


class QueriesToSlackInformationMapping(Base):
    __tablename__ = "queries_to_slack_information_mapping"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    slack_message_information_id = Column(
        BigInteger, ForeignKey("slack_message_information.id")
    )
    queries_to_slack_embeddings_records_id = Column(
        BigInteger, ForeignKey("queries_to_slack_embeddings_records.id")
    )
    dot_product_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"""<QueriesToSlackInformationMapping(slack_message_information_id='{self.slack_message_information_id}',
        queries_to_slack_embeddings_records_id='{self.queries_to_slack_embeddings_records_id}',
        dot_product_score='{self.dot_product_score}',)>"""
