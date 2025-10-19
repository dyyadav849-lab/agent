-- +migrate Up
CREATE TABLE slack_message_information (
    id                          BIGSERIAL,
    CONSTRAINT uk_channel_ts_id      UNIQUE(channel_id, main_thread_ts),
    channel_id                  VARCHAR(255) NOT NULL,
    main_thread_ts              VARCHAR(255) NOT NULL,
    is_embedded                 BOOLEAN DEFAULT FALSE,
    chat_summary                TEXT NOT NULL,
    chat_history                JSON NOT NULL,
    created_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX index_slack_message_information_created_at ON slack_message_information (created_at);
CREATE INDEX index_slack_message_information_updated_at ON slack_message_information (updated_at);

-- +migrate Down
DROP TABLE IF EXISTS slack_message_information;
