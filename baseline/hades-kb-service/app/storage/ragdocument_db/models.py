from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Text,
    func,
    text,
)
from sqlalchemy.ext.declarative import declarative_base

from app.storage.ragdocument_db.constant import ACTIVE_STATUS

Base = declarative_base()


class DocumentCollection(Base):
    __tablename__ = "document_collection"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    uuid = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default=ACTIVE_STATUS)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"""<DocumentCollection(name='{self.name})>"""


class DocumentEmbedding(Base):
    __tablename__ = "document_embedding"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    token_number = Column(BigInteger, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    document_information_id = Column(BigInteger, ForeignKey("document_information.id"))
    text_snipplet = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default=ACTIVE_STATUS)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"""<DocumentEmbedding(embedding='{self.embedding}',
        token_number='{self.token_number}'
        document_information_id='{self.document_information_id}'>"""


class DocumentInformation(Base):
    __tablename__ = "document_information"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    file_path = Column(Text, nullable=False)
    filename = Column(Text, nullable=False)
    file_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default=ACTIVE_STATUS)
    document_last_updated = Column(DateTime(timezone=False), server_default=func.now())
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"""<DocumentInformation(file_path='{self.file_path}',
        file_type='{self.file_type}'
        document_last_updated_at='{self.document_last_updated_at}'>"""


class DocumentCollectionMapping(Base):
    __tablename__ = "document_collection_mapping"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    document_information_id = Column(BigInteger, ForeignKey("document_information.id"))
    document_collection_uuid = Column(
        BigInteger, ForeignKey("document_collection.uuid")
    )
    status = Column(Text, nullable=False, default=ACTIVE_STATUS)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"""<DocumentCollectionMapping(document_information_id='{self.document_information_id}',
        document_collection_uuid='{self.document_collection_uuid}'>"""
