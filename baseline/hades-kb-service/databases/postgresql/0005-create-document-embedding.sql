-- +migrate Up
CREATE TABLE document_embedding (
    id BIGSERIAL,
    token_number  BIGINT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    document_information_id BIGINT NOT NULL,
    text_snipplet TEXT NOT NULL,
    status VARCHAR(255) NOT NULL,
    created_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX index_document_embedding_created_at ON document_embedding(created_at);
CREATE INDEX index_document_embedding_updated_at ON document_embedding(updated_at);
CREATE INDEX index_document_embedding_document_information_id ON document_embedding(document_information_id);
CREATE INDEX index_document_embedding_status ON document_embedding(status);

-- +migrate Down
DROP TABLE IF EXISTS document_embedding;
