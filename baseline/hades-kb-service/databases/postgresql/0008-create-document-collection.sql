-- +migrate Up
CREATE TABLE document_collection (
    id BIGSERIAL,
    uuid VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL,
    created_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX index_document_collection_created_at ON document_collection(created_at);
CREATE INDEX index_document_collection_updated_at ON document_collection(updated_at);
CREATE INDEX index_document_collection_uuid ON document_collection(uuid);
CREATE INDEX index_document_collection_status ON document_collection(status);
ALTER TABLE document_collection
ADD CONSTRAINT uk_document_collection_uuid_unique UNIQUE(uuid);

-- +migrate Down
DROP TABLE IF EXISTS document_collection;
