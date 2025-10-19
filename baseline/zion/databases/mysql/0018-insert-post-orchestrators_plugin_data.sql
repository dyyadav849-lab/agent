-- +migrate Up
INSERT INTO `zion`.`agent_plugin` (
    `schema_version`,
    `name_for_model`,
    `name_for_human`,
    `description_for_model`,
    `description_for_human`,
    `type`,
    `api`,
    `is_moved`,
    `http_plugin_detail`,
    `orchestrators_plugin`
) VALUES (
    '1.0',
    'kibana_post_orchestrator',
    'Post ocherstrator Kibana Log Search',
    'This is postorchestrator for kibana log search formatting',
    'Post instruction for kibana tool',
    'orchestrator',
    '{
        "access_control": {
            "agents": {
                "ti-bot-dm": {},
                "test-token-secret": {},
                "ti-bot-level-zero": {}
            }
        }
    }',
    '0',
    NULL,
    '{
  "formatter": {
    "prompt": "This is a sample prompt for the formatter.",
    "target_tool": "kibana_log_search"
  },
  "orchestrator": {
    "action": "post",
    "prompt": "This is a sample prompt for the orchestrator.",
    "next_tool": "",
    "target_tool": "kibana_log_search"
  }
}'
);

-- +migrate Down
DELETE FROM
  `zion`.`agent_plugin`
WHERE
  `name_for_model` = 'kibana_post_orchestrator';
