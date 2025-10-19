-- +migrate Up

INSERT INTO `zion`.`agent_plugin` (`schema_version`, `name_for_model`, `name_for_human`, `description_for_model`, `description_for_human`, `type`, `api`, `is_moved`) VALUES ('1.0', 'universal_search', 'Universal Search', 'Used to search internal documentations regarding engineering, server services, products, learning, bulletin', 'Uses Universal Search to search Internal Documentation', 'common', '{
        "access_control": {
            "agents":{
                "ti-bot-dm": {},
                "ti-bot-level-zero": {}
            }
        }
    }', '0');

INSERT INTO `zion`.`agent_plugin` (`schema_version`, `name_for_model`, `name_for_human`, `description_for_model`, `description_for_human`, `type`, `api`, `is_moved`) VALUES ('1.0', 'glean_search', 'Glean Search', 'Used to search internal documentations regarding engineering, products', 'Uses Glean Search to search Internal Documentation', 'common', '{
    "access_control": {
        "agents":{
            "ti-bot-dm": {},
            "ti-bot-level-zero": {}
        }
    }
}', '0');

INSERT INTO `zion`.`agent_plugin` (`schema_version`, `name_for_model`, `name_for_human`, `description_for_model`, `description_for_human`, `type`, `api`, `is_moved`) VALUES ('1.0', 'gitlab_job_trace', 'Gitlab Job Trace Search', 'Used to get job trace metadata for gitlab job links attached by user in their messages', 'Uses Gitlab API to read through gitlab job trace attached in messages', 'common', '{
        "access_control": {
            "agents":{
                "ti-bot-dm": {},
                "ti-bot-level-zero": {}
            }
        }
    }', '0');

-- +migrate Down
DELETE FROM  `zion`.`agent_plugin` WHERE `name_for_model` = 'universal_search';

DELETE FROM  `zion`.`agent_plugin` WHERE `name_for_model` = 'glean_search';

DELETE FROM  `zion`.`agent_plugin` WHERE `name_for_model` = 'gitlab_job_trace';
