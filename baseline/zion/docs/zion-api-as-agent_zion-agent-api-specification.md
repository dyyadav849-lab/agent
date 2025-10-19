## Zion Server Config

**Base URL**

- Staging domain: <https://zion.stg.mngd.int.engtools.net/>

- Production domain: <https://zion.mngd.int.engtools.net/>


## Zion Agent Invoke API

> For invoking the LLM Agent
> URL: `/agent/:agent_name/invoke`

### > API Request:

#### **ZionAgentInput**

| Name | Description | Type | Default value | Mandatory |
| --- | --- | --- | --- | --- |
| input | The input message for the current execution | string |  | Yes |
| chat_history | The chat history for the Agent to understand the historical context | list[[ChatHistory](#chathistory)] | [] | No |
| system_prompt | The system prompt for LLM Agent.<br/><br/>Variables supported. E.g. You are an Agent | string | `You are helpful AI assistant in Grab, you helped answer user enquiry.` | No |
| system_prompt_hub_commit | The system prompt configured on  LangSmith prompt hub. Use the prompt string as the value, format: `{prompt-hub-namespace}/{prompt-name}`<br/><br/>The value configured for `system_prompt` property will get ignored when this property is presented | string |  | No |
| system_prompt_variables | The placeholder values used in the `system_prompt` or the `system_prompt_hub_commit`.<br/><br/>The object key expected to be the placeholder key while the object value will be used in the key. | object |  | No |
| structured_response_schema | Structured response schema allow user to , refer the CURL example above for the ideas. | object |  | No |
| structured_response_schema_hub_commit | Similar to `system_prompt_hub_commit`, you could also define the structure on the LangSmith prompt hub, but it expected to be a YAML format for now. | string |  | No |
| agent_config | The detailed configuration of the Agent. Learn more from the AgentConfig. | [AgentConfig](#agentconfig) |  | No |
| query_source | Provide the metadata information for the current LLM invocation | [QuerySource](#querysource) |  | No |

#### ChatHistory

| Name | Description | Default value | Mandatory |
| --- | --- | --- | --- |
| type | The actor type in the conversation history<br/><br/>`human` \| `ai` |  | Yes |
| content | The message of the actor |  | Yes |

#### **AgentConfig**

| Name | Description | Type | Default Value | Mandatory |
| --- | --- | --- | --- | --- |
| tracing | Setting for LangSmith tracing | [AgentTracing](#agenttracing) |  | No |
| plugins | Plugins included for the current LLM invocation | list[[AgentPlugin](#agentplugin)] |  | No |
| llm_model | Only Azure OpenAI is supported now | [AzureOpenAIConfig](#azureopenaiconfig) |  | No |
| agent_executor_config | Advanced setting for the LLM Agent | [AgentExecutorConfig](#agentexecutorconfig) |  | No |

#### QuerySource

| Name | Description | Type | Default Value | Mandatory |
| --- | --- | --- | --- | --- |
| username | The LDAP name of user request | string |  | No |
| channel_name | The Slack channel name of the origin channel | string |  | No |

#### AgentTracing

| Name | Description | Type | Default Value | Mandatory |
| --- | --- | --- | --- | --- |
| hide_input | Mask inputs from the LangSmith tracing.<br/><br/>Available options<br/><br/>- `mask_info` - Only mask the input, chat_history and prompt, tool call sequence and token usages will still captured in the LangSmith run tracing.<br/><br/><br/>- `hide_all` - Hide all info, tool call sequence and token usages WILL NOT be captured in the LangSmith run tracing.<br/><br/><br/>- `off` - Not hiding or masking any info<br/> | enum | off | No |
| hide_output | Mask outputs from the LangSmith tracing.<br/><br/>Available options<br/><br/>- `mask_info` - Only mask the input, chat_history and prompt, tool call sequence and token usages will still captured in the LangSmith run tracing.<br/><br/><br/>- `hide_all` - Hide all info, tool call sequence and token usages WILL NOT be captured in the LangSmith run tracing.<br/><br/><br/>- `off` - Not hiding or masking any info<br/> | enum |  | No |
| tags | The tags to be attached in to the LangSmith tracing. | list[string] |  | No |

#### AgentPlugin

| Name | Description | Type | Default Value | Mandatory |
| --- | --- | --- | --- | --- |
| name | Plugin name | string |  | Yes |
| type | Available options:<br/><br/>- `common` - The first class tool provided by Zion service<br/><br/><br/>- `openapi` - The ChatGPT plugin like plugin. Refer to [TI Bot Agent Plugin](https://helix.engtools.net/docs/default/component/ti-support-bot/ti-bot-agent_ti-bot-agent-plugins_getting-started)<br/> | Enum |  | Yes |
| metadata | Providing metadata as extra setting/configuration for a plugin | object |  | No |

#### AzureOpenAIConfig

| Name | Description | Type | Default Value | Mandatory |
| --- | --- | --- | --- | --- |
| auzre_deployment | The Azure OpenAI deployment version | string | 2024-02-15-preview | No |
| temperature | Range between 0 to 1 | decimal | 0 | No |
| timeout | Unit: Seconds | number | 300 | No |
| streaming | Whether to enabling streaming for an Agent or not | boolean | True | No |
| api_key | The GrabGPT key | string | <shared-api-key-configured-in-zion> | No |

#### AgentExecutorConfig

| Name | Description | Type | Default Value | Mandatory |
| --- | --- | --- | --- | --- |
| max_iterations | The max iterations of the steps can be perform by a LLM Agent.<br/><br/>Note: The number should be set in a reasonable number to avoid infinite loops. | number | 15 | No |

### > API Response:

#### ZionAgentOutput (Response object)

| Name | Description | Type |
| --- | --- | --- |
| structured_response | Structured response is a dictionary of key-value pairs returned by the agent which defined in [ZionAgentInput](#zionagentinput)'s `structured_response_schema` | object |
| agent_execution_trail_id | The Audit trail ID for an execution. | string |
| agent_actions | The list of actions done by the Agent per execution | [ZionAgentAction](#zionagentaction) |
| langsmith_run_id | The LangSmith Run ID that useful to identify the LLM run trace on LangSmith tracing dashboard | string |

#### ZionAgentAction

| Name | Description | Type |
| --- | --- | --- |
| tool | The name of the tool | string |
| tool_input | The input passed into a tool | string \| object |
| tool_output | The output returned by a tool | any |

Zion Agent plugins API

## Zion Agent plugins API

> To get the list of plugins available to the agent
> URL: `/agent-plugins/:agent_name`

### > Response

| Name | Description | Type |
| --- | --- | --- |
| schema_version | Schema version. Always returning `"1.0"` for now | string |
| name_for_model | Plugin's constant name | string |
| name_for_human | Plugin's display name | string |
| description_for_model | Description for LLM Agent, which will be send along with the LLM tools | string |
| description_for_human | Description for user | string |
| type | Available options:<br/><br/>- `common` - The first class tool provided by Zion service<br/><br/><br/>- `openapi` - The ChatGPT plugin like plugin using OpenAPI specification<br/> | enum |
| api | Only `openapi` type has this attribute for now which is the plugin definition | object |

## Sample CURL requests for /agent/:agent_name/invoke API

??? note "Simple CURL request with minimal configuration"
    ```
    curl --location 'http://localhost:8000/agent/<agent-name>/invoke' \
    --header 'agent-secret: <agent-secret>' \
    --header 'Content-Type: application/json' \
    --data '{
        "input": {
            "input": "Write me a poem about the Grab services"
        }
    }'
    ```

??? note "Complex CURL request with most option configured"
    ```
    curl --location 'http://localhost:8000/agent/<agent-name>/invoke' \
    --header 'agent-secret: <agent-secret>' \
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
