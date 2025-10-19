-- +migrate Up
CREATE TABLE `agent_execution_trail` (
  `id` bigint UNSIGNED AUTO_INCREMENT NOT NULL,
  `agent_name` varchar(255) NOT NULL DEFAULT '',
  `langsmith_run_id` varchar(255) NOT NULL DEFAULT '',
  `langsmith_project_name` varchar(255) NOT NULL DEFAULT '',
  `agent_actions` JSON NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `index_created_at` (`created_at`),
  KEY `index_updated_at` (`updated_at`)
) DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- +migrate Down
DROP TABLE IF EXISTS `agent_execution_trail`;
