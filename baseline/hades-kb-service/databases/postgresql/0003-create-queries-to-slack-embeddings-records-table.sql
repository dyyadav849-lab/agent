-- +migrate Up
CREATE TABLE queries_to_slack_embeddings_records (
    id  BIGSERIAL,
    query_summary   TEXT NOT NULL,
    num_of_embedding_found BIGINT NOT NULL,
    created_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX index_queries_to_slack_embeddings_records_created_at ON queries_to_slack_embeddings_records (created_at);
CREATE INDEX index_queries_to_slack_embeddings_records_updated_at ON queries_to_slack_embeddings_records (updated_at);

-- +migrate Down
DROP TABLE IF EXISTS queries_to_slack_embeddings_records;
