# Evaluation Data Collection Pipeline

Automated daily pipeline that collects evaluation data from Hades KB and TI Support, then runs LangSmith evaluations.

## Overview

1. **Data Collection**: Collects user queries from TI Support and chat summaries from Hades KB
2. **Data Merging**: Matches conversations by thread_ts and channel_id
3. **LangSmith Upload**: Creates evaluation dataset with input/expected output pairs
4. **Automatic Evaluation**: Runs model evaluation on the collected data

## Automatic Scheduler

The pipeline runs automatically daily via Ragnarok scheduler:

```bash
# Complete daily evaluation (data collection + model evaluation)
GET /run_job/daily_evaluation
```

**What it does:**
1. Collects data from Hades KB and TI Support
2. Creates dataset: `auto_evals_data_YYYYMMDD`
3. Runs LangSmith evaluation on ti-bot-level-zero agent
4. Results available in LangSmith for analysis

## Manual Usage

```bash
# Data collection only
POST /data-collection-pipeline

# With custom dataset name
POST /data-collection-pipeline
Content-Type: application/json
{"dataset_name": "custom_eval_data_20241220"}
```

## Configuration

Hardcoded settings:
- **Channels**: Specific Slack channel IDs with known data
- **Time period**: Last 1 day
- **Agent**: ti-bot-level-zero with multi-agent config
- **LangSmith project**: ti-bot

## Monitoring

- **Logs**: Structured logging in Zion logs
- **Dataset**: Auto-created in LangSmith as `auto_evals_data_YYYYMMDD`
- **Evaluation results**: Available in LangSmith experiments
