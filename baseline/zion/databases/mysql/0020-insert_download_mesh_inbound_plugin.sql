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
    'download_mesh_inbound',
    'Get Inbound Config',
    ' ',
    'Allow GPT to get inbound config for given service_name and env. This is used to determine if the service_name is VM or MEKS based on compute_types',
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
  `name_for_model` = 'download_mesh_inbound';
