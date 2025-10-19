-- +migrate Up
CREATE TABLE queries_to_slack_information_mapping (
    id BIGSERIAL,
    slack_message_information_id BIGINT NOT NULL,
    queries_to_slack_embeddings_records_id BIGINT NOT NULL,
    dot_product_score  FLOAT NOT NULL,
    created_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);


CREATE INDEX index_queries_to_slack_information_mapping_created_at ON queries_to_slack_information_mapping (created_at);
CREATE INDEX index_queries_to_slack_information_mapping_updated_at ON queries_to_slack_information_mapping (updated_at);


-- +migrate Down
DROP TABLE IF EXISTS queries_to_slack_information_mapping;
