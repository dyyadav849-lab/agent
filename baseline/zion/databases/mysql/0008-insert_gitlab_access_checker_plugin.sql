-- +migrate Up
INSERT INTO `zion`.`agent_plugin` (
    `schema_version`,
    `name_for_model`,
    `name_for_human`,
    `description_for_model`,
    `description_for_human`,
    `type`,
    `api`,
    `is_moved`
) VALUES (
    '1.0',
    'gitlab_repository_access_checker_tool',
    'Repository Access Checker',
    ' ',
    'Allow GPT to get data on how user can get access to a Gitlab Repo',
    'common',
    '{
        "access_control": {
            "agents": {
                "flip": {},
                "ti-bot-dm": {},
                "test-token-secret": {},
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
  `name_for_model` = 'gitlab_repository_access_checker_tool';
