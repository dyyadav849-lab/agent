-- +migrate Up
CREATE TABLE document_information (
    id BIGSERIAL,
    file_path VARCHAR(255) NOT NULL,
    file_type VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL,
    document_last_updated        TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    created_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX index_document_information_created_at ON document_information(created_at);
CREATE INDEX index_document_information_updated_at ON document_information(updated_at);
CREATE INDEX index_document_information_status ON document_information(status);

-- +migrate Down
DROP TABLE IF EXISTS document_information;
