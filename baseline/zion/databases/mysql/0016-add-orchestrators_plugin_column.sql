-- +migrate Up
ALTER TABLE `agent_plugin`
ADD COLUMN `orchestrators_plugin` JSON;

-- +migrate Down
ALTER TABLE `agent_plugin`
DROP COLUMN `orchestrators_plugin`;
