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
    'jira_jql_search',
    'Jira JQL Search',
    '',
    'Search Jira using JQL query',
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
  `name_for_model` = 'jira_jql_search';
