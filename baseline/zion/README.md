# zion

Zion - The LLM agents service

## Getting started

### Quick start

```shell
# Install Poetry (If you don't have it)
$ pip install -U poetry

# Enter the poetry shell (venv)
$ poetry env activate

# Install dependencies
$ poetry install

# Create a gitignored secret file, and fill in the required secrets for development
$ cp configs/secret.ini.example configs/secret.ini

# Setup pre-commit hooks (To discover lint errors before CI/CD pipeline runs)
$ make setup-pre-commit

# Run the project with hot reload (Checkout `Debugging code in VS Code` section if you need debugging)
$ make dev

# Checkout all available commands with
$ make help
```

### Debugging code in VS Code

Create `launch.json` under the `.vscode` folder in the root directory of the project. Add the following configurations:

This allowed you to run the project with hot reload and debug the code in Visual Studio Code.

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run Zion env",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "zion.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload"
            ],
            "env":{
                "AWS_ACCESS_KEY_ID":"",
                "AWS_SECRET_ACCESS_KEY":"",
                "AWS_SESSION_TOKEN":""
            }
        },
    ]
}
```

### Secrets
To access Vault, apply for the ApexTools > zion role in Concedo

### Configuring python environment

Making sure the `python` command in your CLI is pointing to at least `3.11.0` version. If it's not simply use `pyenv` to install the required version.

```shell
# Install pyenv
$ brew install pyenv
# Install the required python version and set it as global
$ pyenv install 3.11.7
$ pyenv global 3.11.7
# See https://github.com/pyenv/pyenv?tab=readme-ov-file#homebrew-in-macos for full guide
```

### Database migrations

The setup is identical to Grab-kit's database migrations. You can run the following commands to create and run migrations.

```shell
# One time setup
$ ./scripts/db.sh --create

# Run migrations
$ ./scripts/db.sh --up
```

## Quick start to test the APIs

The API documentation is available to view at [http://localhost:8000/docs](http://localhost:8000/docs)

### Invoking an agent

```shell
curl --location 'http://localhost:8000/agent/ti-bot-level-zero/invoke' \
--header 'agent-secret;' \
--header 'Content-Type: application/json' \
--data '{
    "input": {
        "system_prompt": "You are a helpful AI assistant providing weather information. Weather today in SEA countries:\n The weather in Kuala Lumpur today is {kl_weather}\nThe weather in Singapore today is {sg_weather}",
        "input": "What is the weather of KL today?",
        "system_prompt_variables": {
            "kl_weather": "cloudy",
            "sg_weather": "windy"
        },
        "chat_history": [{
            "type": "human",
            "content": "Sum of 1+1?"
        }, {
            "type": "ai",
            "content": "2"
        }],
        "agent_config": {
            "tracing": {
                "hide_input": "mask_info",
                "hide_output": "mask_info",
                "tags": ["weather"]
            },
            "llm_model": {
                "azure_deployment": "gpt-4-32k", # optional parameter
                "model_name": "azure/gpt-4-32k"
                "temperature": 0.5
            },
            "plugins": [{
                "name": "calculator",
                "type": "common"
            }, {
                "name": "universal_search",
                "type": "common",
                "metadata": {
                    "attribute_filter": {
                        "sample": "To Do"
                    }
                }
            }],
            "agent_executor_config": {
                "max_iterations": 15,
            }
        },
        "structured_response_schema": {
            "iata_code": {
                "description": "Location of weather, provide this value if the location it's a city and has its IATA code",
                "value_type": "string"
            }
        }
    }
}'
```

#### Configuring agent type

In the API call, you can define the agent type.

```shell
    "agent_config": {
        "agent_type": "multi_agent", // OR react_agent OR agent_executor  
        ...
    }
```

#### Configuring agent plugins

In the API call, additional data can be passed into each agent plugin via the `metadata` field in the `plugins` list.
Information on the available `metadata` fields for each plugin can be found in the respective plugin/tool class definitions. For example, the available metadata fields for the glean_search tool can be found here: https://gitlab.myteksi.net/techops-automation/gate/zion/-/blob/master/zion/tool/glean_search.py#L105.

```shell
"plugins": [
    {
        "name": "glean_search",
        "type": "common",
        "metadata": {
            "wiki_space_collection": [
                "Deployment Automation"
            ],
            "datasourcesFilter": [
                "confluence",
                "techdocs"
            ],
            "techdocs_platform_name_collection": [
                "conveyor"
            ]
        }
    }
]
```

### Submit a feedback of LangSmith run

```shell
curl --location 'http://localhost:8000/agent/ti-bot-level-zero/feedback' \
--header 'agent-secret;' \
--header 'Content-Type: application/json' \
--data '{
    "run_id": "545f3fe6-2464-4402-941d-700a5ac1734b",
    "key": "yujie.ang",
    "score": 1,
    "value": 1,
    "comment": "The answer is perfect"
}'
```

### Get agent plugins

```shell
curl --location --request GET 'http://localhost:8000/agent-plugin/<your-agent-name>?slack_channels=%23ask-tibots&plugin_keyword=univer&users=boonzhan.chew' \
--header 'agent-secret;' \
--data-raw ''
```

### Trigger batch job

Checkout the available job in `zion/jobs/job_runner.py`

```shell
curl --location --request GET 'http://localhost:8000/run_job/<job-name>' \
--header 'agent-secret;' \
--data-raw ''
```

### Running a end-to-end tests of LLM Agent

This is an endpoint to run an end-to-end test for the configured LLM agent. The test execution can be seen on LangSmith's Datasets & Testing dashboard. E.g [Test cases for ti-bot-level-zero](https://langsmith.stg.cauldron.myteksi.net/o/2e19f917-973e-4822-a1a2-679bdaa22cdc/datasets/0d90d003-e6b6-43d5-90f3-b9c2789924d1?paginationState=%7B%22pageIndex%22%3A0%2C%22pageSize%22%3A10%7D)

```shell
curl --location --request POST 'http://localhost:8000/agent/ti-bot-level-zero/langsmith-eval/ti_bot_level_zero_agent' \
--header 'agent-secret;' \
--data ''
```


### AWS Connection

1. Run command below to install aws cli into local machine
    ```sh
    brew install awscli
    ```
2. Navigate to `https://grab-sso.awsapps.com/start` and retrieve your access key from either account
3. Replace your credentials in local machine environment envriable or launch.json if you run with debugging mode, refer to above [launch.json reference](#debugging-code-in-vs-code)
