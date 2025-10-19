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
    'rag_document_kb_search',
    'Document Knowledge Base RAG Search',
    ' ',
    'Allow GPT to search through custom RAG Document KB',
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
  `name_for_model` = 'rag_document_kb_search';
