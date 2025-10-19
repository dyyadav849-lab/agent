-- +migrate Up
-- Add new columns
ALTER TABLE evaluation_results
    ADD COLUMN model_name VARCHAR(255) NULL,
    ADD COLUMN channel_name VARCHAR(255) NULL;

ALTER TABLE evaluation_results
    ADD COLUMN slack_url VARCHAR(512) NULL;

-- Add new index
CREATE INDEX idx_evaluation_results_channel_name ON evaluation_results(channel_name);

CREATE INDEX idx_evaluation_results_slack_url ON evaluation_results(slack_url);

-- +migrate Down
-- Remove the added columns
ALTER TABLE evaluation_results
    DROP COLUMN model_name,
    DROP COLUMN channel_name;

ALTER TABLE evaluation_results
    DROP COLUMN slack_url;

-- Remove the added index
DROP INDEX idx_evaluation_results_channel_name ON evaluation_results;

DROP INDEX idx_evaluation_results_slack_url ON evaluation_results;
