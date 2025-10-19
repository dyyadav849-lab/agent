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
    'gitlab_endpoint',
    'Get Service Endpoint',
    ' ',
    'Allow GPT to get endpoint related information for a service.',
    'common',
    '{
        "access_control": {
            "agents": {
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
  `name_for_model` = 'gitlab_endpoint';
