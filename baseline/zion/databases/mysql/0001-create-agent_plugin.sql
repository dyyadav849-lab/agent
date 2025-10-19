-- +migrate Up
CREATE TABLE `agent_plugin` (
  `id` bigint UNSIGNED AUTO_INCREMENT NOT NULL,
  `schema_version` varchar (255) NOT NULL DEFAULT '',
  `name_for_model` varchar(255) NOT NULL DEFAULT '',
  `name_for_human` varchar(255) NOT NULL DEFAULT '',
  `description_for_model`varchar(255) NOT NULL DEFAULT '',
  `description_for_human`varchar(255) NOT NULL DEFAULT '',
  `type`varchar(255) NOT NULL DEFAULT '',
  `api` JSON NOT NULL ,
  `is_moved` boolean NOT NULL default 0,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `index_name_for_model` (`name_for_model`),
  KEY `index_is_moved` (`is_moved`),
  KEY `index_type` (`type`),
  KEY `index_created_at` (`created_at`),
  KEY `index_updated_at` (`updated_at`)
) DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- +migrate Down
DROP TABLE IF EXISTS `agent_plugin`;
