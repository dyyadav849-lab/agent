-- +migrate Up
ALTER TABLE `agent_plugin`
ADD COLUMN `owner` JSON;

-- +migrate Down
ALTER TABLE `agent_plugin`
DROP COLUMN `owner`;
