-- +migrate Up

UPDATE `zion`.`agent_plugin` SET `name_for_model` = "slack_conversation_tool" WHERE (`name_for_model` = 'hades_knowledge_base_tool');

-- +migrate Down

UPDATE `zion`.`agent_plugin` SET `name_for_model` = "hades_knowledge_base_tool" WHERE (`name_for_model` = 'slack_conversation_tool');
