-- +migrate Up
CREATE TABLE document_collection_mapping (
    id BIGSERIAL,
    document_information_id  BIGINT NOT NULL,
    document_collection_uuid VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL,
    created_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX index_document_collection_mapping_created_at ON document_collection_mapping(created_at);
CREATE INDEX index_document_collection_mapping_updated_at ON document_collection_mapping(updated_at);

-- +migrate Down
DROP TABLE IF EXISTS document_collection_mapping;
