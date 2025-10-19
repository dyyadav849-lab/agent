-- +migrate Up
CREATE TABLE evaluation_results (
    id BIGINT UNSIGNED AUTO_INCREMENT,
    agent_name VARCHAR(255) NOT NULL,
    test_project_name VARCHAR(255) NOT NULL,
    test_run_name VARCHAR(255) NOT NULL,
    experiment_name VARCHAR(255) NOT NULL,
    run_id VARCHAR(255) NOT NULL,
    run_name VARCHAR(255) NOT NULL,
    run_type VARCHAR(255) NOT NULL,
    dataset_id VARCHAR(255) NOT NULL,
    example_id VARCHAR(255) NOT NULL,
    input_text TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    actual_output TEXT,
    tool_score FLOAT,
    rouge_score FLOAT,
    llm_judge_score FLOAT,
    grading_note_score FLOAT,
    llm_judge_comment TEXT,
    grading_note_comment TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY index_created_at (created_at),
    KEY index_updated_at (updated_at)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE INDEX index_created_at ON evaluation_results(created_at);
CREATE INDEX index_updated_at ON evaluation_results(updated_at);
CREATE INDEX index_evaluation_results_agent_name ON evaluation_results(agent_name);
CREATE INDEX index_evaluation_results_test_project_name ON evaluation_results(test_project_name);
CREATE INDEX index_evaluation_results_run_id ON evaluation_results(run_id);
CREATE INDEX index_evaluation_results_example_id ON evaluation_results(example_id);

-- +migrate Down
DROP TABLE IF EXISTS evaluation_results;
