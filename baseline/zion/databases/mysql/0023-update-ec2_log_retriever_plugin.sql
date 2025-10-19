-- +migrate Up
UPDATE agent_plugin SET description_for_human = 'Allow GPT to get log data of EC2, ELB, ASG, and DDB' WHERE name_for_model ='ec2_log_retriever';
;
-- +migrate Down
UPDATE agent_plugin SET description_for_human = 'Allow GPT to get log data of EC2' WHERE name_for_model ='ec2_log_retriever';
