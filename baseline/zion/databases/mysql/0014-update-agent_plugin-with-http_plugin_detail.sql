-- +migrate Up
ALTER TABLE `agent_plugin`
ADD COLUMN `http_plugin_detail` JSON;

-- +migrate Down
ALTER TABLE `agent_plugin`
DROP COLUMN `http_plugin_detail`;
