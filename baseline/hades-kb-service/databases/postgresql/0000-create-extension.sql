-- +migrate Up
CREATE EXTENSION IF NOT EXISTS vector;

-- +migrate Down
DROP EXTENSION IF EXISTS vector CASCADE;
