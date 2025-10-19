-- +migrate Up
CREATE TABLE slack_message_embedding (
    id                          BIGSERIAL,
    token_number                BIGINT NOT NULL,
    embedding                   VECTOR(1536) NOT NULL,
    slack_message_information_id BIGINT NOT NULL,
    created_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX index_slack_message_embedding_created_at ON slack_message_embedding (created_at);
CREATE INDEX index_slack_message_embedding_updated_at ON slack_message_embedding (updated_at);
CREATE INDEX index_embedding ON slack_message_embedding USING ivfflat (embedding vector_ip_ops) WITH (lists = 100);

-- +migrate Down
DROP TABLE IF EXISTS slack_message_embedding;
