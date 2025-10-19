-- +migrate Up

UPDATE `zion`.`agent_plugin` SET `description_for_model` = "" WHERE (`name_for_model` = 'universal_search');

UPDATE `zion`.`agent_plugin` SET `description_for_model` = "" WHERE (`name_for_model` = 'glean_search');

UPDATE `zion`.`agent_plugin` SET `description_for_model` = "" WHERE (`name_for_model` = 'gitlab_job_trace');

-- +migrate Down

UPDATE `zion`.`agent_plugin` SET `description_for_model` = "Used to search internal documentations regarding code, engineering, server services, products, learning, bulletin or other general internal documentation inside Grab." WHERE (`name_for_model` = 'universal_search');

UPDATE `zion`.`agent_plugin` SET `description_for_model` = "Used to search internal documentations regarding engineering, products." WHERE (`name_for_model` = 'glean_search');

UPDATE `zion`.`agent_plugin` SET `description_for_model` = "Used to get job trace metadata for gitlab job links attached by user in their messages" WHERE (`name_for_model` = 'gitlab_job_trace');
