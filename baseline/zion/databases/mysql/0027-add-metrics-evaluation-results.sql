-- Add DeepEval evaluation columns to evaluation_results table
ALTER TABLE evaluation_results
ADD COLUMN contextual_relevancy_score FLOAT,
ADD COLUMN contextual_relevancy_comment TEXT,
ADD COLUMN faithfulness_score FLOAT,
ADD COLUMN faithfulness_comment TEXT,
ADD COLUMN contextual_recall_score FLOAT,
ADD COLUMN contextual_recall_comment TEXT;
