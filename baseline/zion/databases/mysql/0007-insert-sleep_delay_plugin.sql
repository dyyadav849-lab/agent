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
    'sleep_delay',
    'Delay Tool',
    '',
    'Allow GPT to have sleep/delay before performing the next action',
    'common',
    '{
      "access_control": {
          "agents":{
              "ti-bot-dm": {
                "users": [
                    "sameer.jha",
                    "yuxin.goh",
                    "yonglian.hii",
                    "russell.ong",
                    "swapnil.mirkute"
                ]
              },
              "ti-bot-level-zero": {
                 "slack_channels": [
                    "#ask-interactive-comms",
                    "#ask-chat-and-voice",
                    "#ask-channel--staging"
                ]
              }
          }
      }
    }',
    '0'
  );

-- +migrate Down
DELETE FROM
  `zion`.`agent_plugin`
WHERE
  `name_for_model` = 'sleep_delay';
