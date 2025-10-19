-- +migrate Up
INSERT INTO
  `zion`.`agent_plugin` (
    `schema_version`,
    `name_for_model`,
    `name_for_human`,
    `description_for_model`,
    `description_for_human`,
    `type`,
    `api`,
    `is_moved`
  )
VALUES
  (
    '1.0',
    'knowledge_base_search',
    'Knowledge Base Search',
    '',
    'Search internal documentation from the knowledge base service',
    'common',
    '{
      "access_control": {
          "agents":{
              "ti-bot-dm": {},
              "ti-bot-level-zero": {}
          }
      }
    }',
    '0'
  );

-- +migrate Down
DELETE FROM
  `zion`.`agent_plugin`
WHERE
  `name_for_model` = 'knowledge_base_search';
