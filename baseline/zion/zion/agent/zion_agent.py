
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Optional

import yaml
from fastapi import HTTPException
from langchain import hub
from langchain.agents import AgentExecutor
from langchain_community.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
    RunnableSerializable,
)
from langchain_core.tracers.context import LangChainTracer, tracing_v2_enabled
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.pregel import Pregel
from langsmith import Client as LangSmithClient
from llm_kit_guardrails.guardrails import Guardrail
from openai import BadRequestError, NotFoundError
from pydantic import BaseModel

from zion.agent.agent_builder import (
    get_agent_executor,
)
from zion.agent.agent_input_transformer import transform_chat_history
from zion.agent.agent_output_parser import (
    CustomOpenAIToolsAgentOutputParser,
    structured_output_delimiter,
)
from zion.agent.constant import (
    GRABGPT_AGENT_PROFILE_NAME,
    guardrails_error_message,
    guardrails_yaml_content,
    llm_parallel_chain_key,
)
from zion.agent.model import (
    ChatGrabGPT,
    GrabGPTChatModelEnum,
    GrabGPTEnum,
)
from zion.agent.multi_agent.classes import (
    AgentState,
    MultiAgentPrompts,
    MultiAgentStructuredRespDescriptions,
)
from zion.agent.multi_agent.constant import (
    ABLE_TO_ANSWER_DESCRIPTION,
    ABLE_TO_ANSWER_PROMPT,
    ANSWER_CONFIDENCE_SCORE_DESCRIPTION,
    EXPECTED_SLACK_WORKFLOW_CATEGORY_DESCRIPTION,
    INTERNAL_SEARCH_PROMPT,
    QUERY_CATEGORIZER_PROMPT,
    SLACK_WORKFLOW_CATEGORY_DESCRIPTION,
    SOURCES_DESCRIPTION,
    TI_BOT_PROMPT,
)
from zion.agent.multi_agent.multi_agent_workflow import (
    get_ti_bot_multi_agent_system,
)
from zion.agent.react_agent_builder import (
    convert_input_to_react_agent_message_dict,
)
from zion.agent.single_agent.constant import FOLLOW_UP_CONVO_AGENT_PROMPT
from zion.agent.single_agent.single_agent import (
    SingleAgentPrompts,
    SingleAgentState,
    SingleAgentStructuredRespDescriptions,
)
from zion.agent.single_agent.workflow import get_single_agent_system
from zion.agent.zion_agent_classes import (
    AgentType,
    AttributeInfo,
    MaskingMode,
    StructuredResponseSchema,
    ZionAgentInput,
    ZionAgentOutput,
    ZionRunnableConfig,
)
from zion.config import AgentProfile, global_config, is_langsmith_enabled, logger
from zion.data.agent_execution_trail import AgentExecutionTrail, create_trail
from zion.data.agent_plugin.constant import (
    AGENT_COMMON_PLUGIN_TYPE,
    AGENT_HTTP_PLUGIN_TYPE,
    AGENT_OCHESTRATOR_PLUGIN_TYPE,
    AGENT_OPENAPI_PLUGIN_TYPE,
)
from zion.data.agent_plugin.data import QueryAgentPluginRequest
from zion.data.agent_plugin.database_handler import get_agent_plugin_database
from zion.data.agent_plugin.util import get_agent_plugin_map
from zion.tool.agent_plugins import (
    COMMON_PLUGINS,
    AgentPlugin,
    get_tools_from_database_result,
)
from zion.tool.agent_tool import (
    ZionAgentActions,
    get_zion_agent_actions,
    mask_inputs,
    mask_outputs,
)
from zion.tool.gitlab_mr_creation_automation_tool import GitlabMrCreationAutomationTool
from zion.tool.glean_search import GleanSearchTool
from zion.tool.hades_kb_service import HadesKnowledgeBaseTool
from zion.tool.orchestrator_tool import OrchestratorTool
from zion.tool.requests_tool import RequestsTool
from zion.util.common import get_current_time_in_iso8601_sgt


class GuardrailsAgentOutput(BaseModel):
    output: Any


class ZionAgent(RunnableSerializable[ZionAgentInput, ZionAgentOutput]):
    agent_profile: AgentProfile | None = None
    complete_chain: Optional[RunnableParallel] = None

    class Config:
        arbitrary_types_allowed = True

    def _get_chat_open_ai(self: ZionAgent, agent_input: ZionAgentInput) -> ChatGrabGPT:
        openai_api_key = global_config.openai_api_key
        openai_endpoint = global_config.openai_endpoint
        # if aihome-be's grabgpt agent, use aihome openai api key
        if self.agent_profile.profile_name == GRABGPT_AGENT_PROFILE_NAME:
            openai_api_key = global_config.aihome_openai_api_key
            openai_endpoint = global_config.private_openai_endpoint

        base_azure_open_ai_config = {
            # default values
            "api_key": openai_api_key,
            "base_url": f"{openai_endpoint}{GrabGPTEnum.UNIFIED_ENDPOINT_V1}",
            "model_name": GrabGPTChatModelEnum.AZURE_GPT4O,
            "temperature": 0,
            "timeout": 300,
            # We need to set streaming=True on the LLM to support streaming individual tokens.
            # when using the stream_log endpoint.
            # .stream for agents streams action observation pairs not individual tokens.
            "streaming": True,
        }

        if agent_input.agent_config.llm_model is not None:
            # Override the base_config with the input config
            for _, [key, value] in enumerate(agent_input.agent_config.llm_model):
                if value is not None:
                    base_azure_open_ai_config[key] = value

        return ChatGrabGPT(
            model=base_azure_open_ai_config["model_name"],
            extra_body={
                "input_guardrails": {
                    "amazon_bedrock": {
                        "guardrail_name": "grabgpt-api-gateway-guardrail"
                    },
                },
                # we only include input guardrails
                # this is because we set streaming to true, which wont process guardrails anyway
            },
            **base_azure_open_ai_config,
        )

    def _assign_plugin_details_by_plugin_name(
        self, plugin: BaseTool, agent_input: ZionAgentInput, agent_plugin: AgentPlugin
    ) -> None:
        if plugin.name == HadesKnowledgeBaseTool().name:
            plugin.metadata = {"user_prompt": agent_input.input}
        if plugin.name == GleanSearchTool().name:
            glean_search = GleanSearchTool()
            glean_search.replace_glean_description(agent_plugin.metadata)
            plugin.description = glean_search.description

    def _get_tools_from_agent_plugins(  # noqa:C901, PLR0912
        self, agent_plugins: list[AgentPlugin], agent_input: ZionAgentInput
    ) -> list:
        """Get tools from agent_plugins."""
        openapi_plugins: list[AgentPlugin] = []
        tools: list[AgentPlugin] = []

        agent_plugin_db = get_agent_plugin_database(
            query_agent_plugin_req=QueryAgentPluginRequest(
                agent_name=self.agent_profile.profile_name,
                channel_name=agent_input.query_source.channel_name,
                username=agent_input.query_source.username,
            ),
        )

        if agent_plugin_db is None:
            # early return empty arr as we cant find any tools from db
            return []

        # load from database
        agent_plugin_map = get_agent_plugin_map(agent_plugin_db)

        for agent_plugin in agent_plugins:
            if agent_plugin.type == AGENT_COMMON_PLUGIN_TYPE:
                agent_plugin_from_map = agent_plugin_map.get(
                    AGENT_COMMON_PLUGIN_TYPE, {}
                ).get(agent_plugin.name, None)

                if agent_plugin_from_map is None:
                    logger.warn(f"Common tool {agent_plugin.name} not found")
                    continue

                plugin = COMMON_PLUGINS[agent_plugin.name]
                if isinstance(plugin, BaseTool) or issubclass(plugin, BaseTool):
                    plugin = plugin()
                    self._assign_plugin_details_by_plugin_name(
                        plugin, agent_input, agent_plugin
                    )

                if agent_plugin.metadata is not None and isinstance(plugin, BaseTool):
                    plugin.metadata = agent_plugin.metadata

                tools.append(plugin)

            elif agent_plugin.type == AGENT_OCHESTRATOR_PLUGIN_TYPE:
                agent_plugin_from_map = agent_plugin_map.get(
                    AGENT_OCHESTRATOR_PLUGIN_TYPE, {}
                ).get(agent_plugin.name, None)

                if agent_plugin_from_map is None:
                    logger.warn(f"Orchestrator tool {agent_plugin.name} not found")
                    continue

                prompt_tool = OrchestratorTool.generate_orchestrator_plugin(
                    plugin=agent_plugin_from_map
                )

                tools.append(prompt_tool)

            elif agent_plugin.type == AGENT_OPENAPI_PLUGIN_TYPE:
                agent_plugin_from_map = agent_plugin_map.get(
                    AGENT_OPENAPI_PLUGIN_TYPE, {}
                ).get(agent_plugin.name, None)

                if agent_plugin_from_map is None:
                    logger.warn(f"OpenAPI tool {agent_plugin.name} not found")
                    continue

                openapi_plugins.append(agent_plugin_from_map)

            elif agent_plugin.type == AGENT_HTTP_PLUGIN_TYPE:
                agent_plugin_from_map = agent_plugin_map.get(
                    AGENT_HTTP_PLUGIN_TYPE, {}
                ).get(agent_plugin.name, None)

                if agent_plugin_from_map is None:
                    logger.warn(f"HTTP tool {agent_plugin.name} not found")
                    continue

                openapi_plugins.append(agent_plugin_from_map)

        if len(openapi_plugins) > 0:
            tools.append(RequestsTool())
            tools += get_tools_from_database_result(openapi_plugins)

        # add mr creation automation plugin by default
        if agent_input.query_source.channel_name in [
            "#jiatian-test-dev2",
            "#jiatian-test-dev3",
            "#jiatian-test-prd",
            "#chimera-users",
            "#llmops",
        ]:
            mr_creation_tool = GitlabMrCreationAutomationTool()
            mr_creation_tool.metadata = {
                "model_name": agent_input.agent_config.llm_model.model_name,
                "query_source": agent_input.query_source,
            }
            tools.append(mr_creation_tool)

        return tools

    def _get_follow_up_convo_agent(
        self: ZionAgent,
        agent_input: ZionAgentInput,
    ) -> Pregel:
        agent_input.chat_history = transform_chat_history(agent_input.chat_history)

        # Build tools
        agent_plugins = []
        if agent_input.agent_config.plugins is not None:
            agent_plugins = agent_input.agent_config.plugins

        tools = self._get_tools_from_agent_plugins(agent_plugins, agent_input)

        # Load MCP tools asynchronously
        if agent_input.agent_config.mcp_config is not None:
            mcp_servers = agent_input.agent_config.mcp_config
            mcp_tools = asyncio.run(self._load_mcp_tools(mcp_servers))
            tools.extend(mcp_tools)

        return get_single_agent_system(
            tools=tools,
            model=self._get_chat_open_ai(agent_input),
            prompts=SingleAgentPrompts(single_agent_prompt=FOLLOW_UP_CONVO_AGENT_PROMPT),
            descriptions=SingleAgentStructuredRespDescriptions(),
        )

    def _get_multi_agent(
        self: ZionAgent,
        agent_input: ZionAgentInput,
    ) -> Pregel:
        agent_input.chat_history = transform_chat_history(agent_input.chat_history)
        agent_prompts = self._get_multi_agent_prompts(agent_input)
        agent_descriptions = self._get_multi_agent_descriptions(agent_input)

        # Build tools
        agent_plugins = []
        if agent_input.agent_config.plugins is not None:
            agent_plugins = agent_input.agent_config.plugins

        tools = self._get_tools_from_agent_plugins(agent_plugins, agent_input)

        # Load MCP tools asynchronously
        if agent_input.agent_config.mcp_config is not None:
            mcp_servers = agent_input.agent_config.mcp_config
            mcp_tools = asyncio.run(self._load_mcp_tools(mcp_servers))
            tools.extend(mcp_tools)

        return get_ti_bot_multi_agent_system(
            tools=tools,
            model=self._get_chat_open_ai(agent_input),
            prompts=agent_prompts,
            descriptions=agent_descriptions,
        )

    def _get_react_agent(
        self: ZionAgent,
        agent_input: ZionAgentInput,
    ) -> Pregel:
        base_system_prompt = self._get_base_system_prompt(agent_input)
        agent_input.chat_history = transform_chat_history(agent_input.chat_history)

        # Build tools
        agent_plugins = []
        if agent_input.agent_config.plugins is not None:
            agent_plugins = agent_input.agent_config.plugins

        tools = self._get_tools_from_agent_plugins(agent_plugins, agent_input)

        # Load MCP tools asynchronously
        if agent_input.agent_config.mcp_config is not None:
            mcp_servers = agent_input.agent_config.mcp_config
            mcp_tools = asyncio.run(self._load_mcp_tools(mcp_servers))
            tools.extend(mcp_tools)


        return get_single_agent_system(
            tools=tools,
            model=self._get_chat_open_ai(agent_input),
            prompts=SingleAgentPrompts(base_system_prompt),
            descriptions=SingleAgentStructuredRespDescriptions(),
        )

    def _get_agent_executor(
        self: ZionAgent,
        agent_input: ZionAgentInput,
        _config: ZionRunnableConfig | None = None,
    ) -> AgentExecutor:
        """Get the agent executor."""
        system_prompt, system_prompt_variables = self._get_system_prompt(agent_input)
        agent_input.chat_history = transform_chat_history(agent_input.chat_history)

        # Build tools
        agent_plugins = []
        if agent_input.agent_config.plugins is not None:
            agent_plugins = agent_input.agent_config.plugins

        tools = self._get_tools_from_agent_plugins(agent_plugins, agent_input)

        return get_agent_executor(
            chat_open_ai=self._get_chat_open_ai(agent_input),
            system_prompt=system_prompt,
            system_prompt_variables=system_prompt_variables,
            tools=tools,
            input_class=ZionAgentInput,
            max_iterations=agent_input.agent_config.agent_executor_config.max_iterations,
            output_class=ZionAgentOutput,
            output_parser=CustomOpenAIToolsAgentOutputParser,
        )

    def _pull_prompt_hub_commit(self, hub_commit: str) -> str:
        prompt = hub.pull(
            owner_repo_commit=hub_commit,
            api_url=global_config.langchain_endpoint,
            api_key=global_config.langchain_api_key,
        )
        return prompt.template

    # prioritize in order: 1. prompt hub, 2. system_prompt in request, 3. fallback const
    def _get_base_system_prompt(self: ZionAgent, agent_input: ZionAgentInput) -> str:
        base_system_prompt = (
            "You are a helpful AI assistant in Grab helping to answer user enquiries."
        )

        if agent_input.system_prompt:
            base_system_prompt = agent_input.system_prompt

        if agent_input.system_prompt_hub_commit:
            try:
                base_system_prompt = self._pull_prompt_hub_commit(
                    hub_commit=agent_input.system_prompt_hub_commit
                )
            except (
                Exception  # noqa: BLE001, because we want to handle it gracefully
            ) as e:
                logger.error(
                    "[_get_base_system_prompt] Unable to get hub commit, fallback to system_prompt",
                    tags={"err": str(e)},
                )

        prompt_template = PromptTemplate.from_template(base_system_prompt)
        # format prompt template with variables, e.g. channel_specific_instructions, and return str
        return prompt_template.format(
            **(
                agent_input.system_prompt_variables
                if agent_input.system_prompt_variables
                else {"slack_channel_specific_instruction": "N/A"}
            )
        )

    def _get_formatted_agent_prompt(
        self: ZionAgent,
        agent_input: ZionAgentInput,
        prompt_hub_commit: str,
        fallback_prompt: str,
    ) -> str:
        try:
            prompt = self._pull_prompt_hub_commit(
                hub_commit=global_config.langsmith_handle_prefix
                + "/"
                + prompt_hub_commit
            )

            prompt_template = PromptTemplate.from_template(prompt)
            # format prompt template with variables, e.g. channel_specific_instructions, and return str
            return prompt_template.format(
                **(
                    agent_input.system_prompt_variables
                    if agent_input.system_prompt_variables
                    else {"slack_channel_specific_instruction": "N/A"}
                )
            )
        except (
            Exception  # noqa: BLE001, because we want to handle it gracefully
        ) as e:
            logger.error(
                "[_get_multi_agent_prompt] Unable to get hub commit, fallback to default agent prompts",
                tags={"err": str(e)},
            )

        return fallback_prompt

    def _get_multi_agent_prompts(
        self: ZionAgent, agent_input: ZionAgentInput
    ) -> MultiAgentPrompts:
        prompts = MultiAgentPrompts()
        query_categorizer_prompt_hub_commit = "ti-bot-multi-agent-query-categorizer"
        ti_bot_prompt_hub_commit = "ti-bot-multi-agent-ti-bot"
        internal_search_prompt_hub_commit = "ti-bot-multi-agent-internal-search"
        able_to_answer_prompt_hub_commit = "ti-bot-multi-agent-able-to-answer"

        prompts["query_categorizer_agent_prompt"] = self._get_formatted_agent_prompt(
            agent_input, query_categorizer_prompt_hub_commit, QUERY_CATEGORIZER_PROMPT
        )
        prompts["ti_bot_agent_prompt"] = self._get_formatted_agent_prompt(
            agent_input, ti_bot_prompt_hub_commit, TI_BOT_PROMPT
        )
        prompts["internal_search_agent_prompt"] = self._get_formatted_agent_prompt(
            agent_input, internal_search_prompt_hub_commit, INTERNAL_SEARCH_PROMPT
        )
        prompts["able_to_answer_agent_prompt"] = self._get_formatted_agent_prompt(
            agent_input, able_to_answer_prompt_hub_commit, ABLE_TO_ANSWER_PROMPT
        )

        return prompts

    def _get_multi_agent_descriptions(
        self: ZionAgent,
        agent_input: ZionAgentInput,
    ) -> MultiAgentStructuredRespDescriptions:
        descriptions = MultiAgentStructuredRespDescriptions()
        able_to_answer_description_hub_commit = (
            "ti-bot-multi-agent-able-to-answer-description"
        )
        answer_confidence_score_description_hub_commit = (
            "ti-bot-multi-agent-answer-confidence-score-description"
        )
        sources_description_hub_commit = "ti-bot-multi-agent-sources-description"
        slack_workflow_category_description_hub_commit = (
            "ti-bot-multi-agent-category-description"
        )
        expected_slack_workflow_category_description_hub_commit = (
            "ti-bot-multi-agent-expected-category-description"
        )

        descriptions["able_to_answer_description"] = self._get_formatted_agent_prompt(
            agent_input,
            able_to_answer_description_hub_commit,
            ABLE_TO_ANSWER_DESCRIPTION,
        )
        descriptions["answer_confidence_score_description"] = (
            self._get_formatted_agent_prompt(
                agent_input,
                answer_confidence_score_description_hub_commit,
                ANSWER_CONFIDENCE_SCORE_DESCRIPTION,
            )
        )
        descriptions["sources_description"] = self._get_formatted_agent_prompt(
            agent_input,
            sources_description_hub_commit,
            SOURCES_DESCRIPTION,
        )
        descriptions["slack_workflow_category_description"] = (
            self._get_formatted_agent_prompt(
                agent_input,
                slack_workflow_category_description_hub_commit,
                SLACK_WORKFLOW_CATEGORY_DESCRIPTION,
            )
        )
        descriptions["expected_slack_workflow_category_description"] = (
            self._get_formatted_agent_prompt(
                agent_input,
                expected_slack_workflow_category_description_hub_commit,
                EXPECTED_SLACK_WORKFLOW_CATEGORY_DESCRIPTION,
            )
        )

        return descriptions

    def _get_structured_response_schema(
        self: ZionAgent, agent_input: ZionAgentInput
    ) -> dict[str, AttributeInfo] | None:
        structured_response_schema = None

        if agent_input.structured_response_schema_hub_commit:
            try:
                structured_response_schema_yaml_str = self._pull_prompt_hub_commit(
                    hub_commit=agent_input.structured_response_schema_hub_commit
                )
                return StructuredResponseSchema(
                    obj=yaml.safe_load(structured_response_schema_yaml_str)
                ).obj
            except (
                Exception  # noqa: BLE001, because we want to handle it gracefully
            ) as e:
                logger.error(
                    "[_get_structured_response_schema] Unable to get hub commit, fallback to structured_response_schema",
                    tags={"err": str(e)},
                )

        if agent_input.structured_response_schema is not None:
            structured_response_schema = StructuredResponseSchema(
                obj=agent_input.structured_response_schema
            ).obj

        return structured_response_schema

    def _get_system_prompt(
        self: ZionAgent, agent_input: ZionAgentInput
    ) -> tuple[str, dict[str, Any]]:
        base_system_prompt = self._get_formatted_agent_prompt(agent_input)
        # Use f-string to interpolate the "base_system_prompt",
        # as the it may contain other f-string variables defined by API user,
        # This will allow LCEL to replace the variables inside the "base_system_prompt"
        system_prompt = "\n".join(
            (
                f"{base_system_prompt}\n\n",
                f"Current Time: {get_current_time_in_iso8601_sgt()}\n\n",
                "!!!Important!!! You must reply the response with following format regardless if you manage to answer it. {structured_output_instructions}",
                "Format:\n<your answer in markdown format>\n",
            )
        )

        # system_prompt_variables is a dictionary of variables that will be reference as additional variables in LCEL later
        system_prompt_variables: dict[str, Any] = {"structured_output_instructions": ""}
        if agent_input.system_prompt_variables is not None:
            system_prompt_variables.update(agent_input.system_prompt_variables)

        # When structured response schema is provided, construct into the system prompt
        structured_response_schema = self._get_structured_response_schema(agent_input)
        if structured_response_schema is not None:
            structured_response_definitions = [
                f" - {key} ({attr.value_type}): {attr.description}"
                for key, attr in structured_response_schema.items()
            ]

            if len(structured_response_definitions) > 0:
                structured_response_definition_text = "\n".join(
                    structured_response_definitions
                )
                structured_output_prompt = "\n".join(
                    (
                        f"{structured_output_delimiter}",
                        "```json",
                        f"{structured_response_definition_text}",
                        "```",
                    )
                )
                system_prompt += "\n" + structured_output_prompt
                system_prompt_variables["structured_output_instructions"] = (
                    f"Then follow by the delimiter and structured response in JSON markdown codeblock. NEVER CHANGE OR REMOVE '{structured_output_delimiter}'. Please generate a JSON object that includes at least one key. Each key should map to a corresponding value, which can vary in type (e.g., array, object, string, etc.)"
                )

        return system_prompt, system_prompt_variables

    def _log_trail(
        self: ZionAgent,
        tracer: LangChainTracer | None = None,
        agent_actions: list[ZionAgentActions] | None = None,
    ) -> AgentExecutionTrail:
        if agent_actions is None:
            agent_actions = []

        try:
            langsmith_run_id = ""
            agent_actions_dict = [action.json() for action in agent_actions]

            if tracer and tracer.latest_run and tracer.latest_run.id is not None:
                langsmith_run_id = tracer.latest_run.id.__str__()

            return create_trail(
                agent_name=self.agent_profile.profile_name,
                langsmith_project_name=self.agent_profile.langchain_project,
                langsmith_run_id=langsmith_run_id,
                agent_actions=agent_actions_dict,
            )
        except Exception:  # noqa: BLE001, because we want to handle it gracefully
            logger.exception("Failed to log trail")
            return None

    def _get_langsmith_client(
        self: ZionAgent, agent_input: ZionAgentInput
    ) -> LangSmithClient:
        hide_inputs = False
        hide_outputs = False

        if agent_input.agent_config.tracing is not None:
            if agent_input.agent_config.tracing.hide_input == MaskingMode.mask_info:
                hide_inputs = mask_inputs
            elif agent_input.agent_config.tracing.hide_input == MaskingMode.hide_all:
                hide_inputs = True

            if agent_input.agent_config.tracing.hide_output == MaskingMode.mask_info:
                hide_outputs = mask_outputs
            elif agent_input.agent_config.tracing.hide_output == MaskingMode.hide_all:
                hide_outputs = True

        return LangSmithClient(
            api_key=global_config.langchain_api_key,
            api_url=global_config.langchain_endpoint,
            hide_inputs=hide_inputs,
            hide_outputs=hide_outputs,
        )

    def _before_invoke(
        self, config: ZionRunnableConfig | None, agent_input: dict
    ) -> dict:
        if config is not None and "agent_profile" in config.get("configurable", {}):
            self.agent_profile = config.get(
                "configurable",
                {},
            ).get(
                "agent_profile",
                AgentProfile(langchain_project="", profile_name="", secret_key=""),
            )

        if (
            agent_input.get("agent_config") is not None
            and agent_input.get("agent_config", {}).get("llm_model", None) is not None
            and agent_input.get("agent_config", {})
            .get("llm_model", {})
            .get("azure_deployment", None)
            is not None
        ):
            # set the llm model to the correct param
            agent_input["agent_config"]["llm_model"]["model_name"] = (
                f"azure/{agent_input['agent_config']['llm_model']['azure_deployment']}"
            )

            llm_model_dict = agent_input["agent_config"]["llm_model"]

            # delete the azure_deployment from the input
            del llm_model_dict["azure_deployment"]

            agent_input["agent_config"]["llm_model"] = llm_model_dict

        if self.agent_profile is None:
            raise HTTPException(
                status_code=500,
                detail="Agent profile is not provided to the agent executor.",
            )
        return agent_input

    def _handle_invoke_agent(
        self,
        agent_input: dict,
        tags: list[str],
        agent: AgentExecutor | Pregel,
        config: ZionRunnableConfig | None = None,
    ) -> dict:
        typed_input = ZionAgentInput(**agent_input)

        if typed_input.agent_config.agent_type == AgentType.agent_executor:
            complete_chain = RunnableParallel(
                {
                    # guardrail_parallel_chain_key: guardrails_chain,
                    # temporarily disable guardrail chain to make use of api gateway guardrail
                    llm_parallel_chain_key: agent,
                }
            )
            complete_chain_output = complete_chain.invoke(agent_input, config=config)

            return complete_chain_output.get(llm_parallel_chain_key, {})

        def langgraph_wrapper(
            input_data: dict, config: ZionRunnableConfig | None
        ) -> dict:
            if is_langsmith_enabled():
                with tracing_v2_enabled(
                    project_name=self.agent_profile.langchain_project,
                    client=self._get_langsmith_client(typed_input),
                    tags=tags,
                ):
                    return agent.invoke(
                        input=convert_input_to_react_agent_message_dict(
                            ZionAgentInput(**input_data)
                        ),
                        config=config,
                    )
            return agent.invoke(
                input=convert_input_to_react_agent_message_dict(
                    ZionAgentInput(**input_data)
                ),
                config=config,
            )

        complete_chain = RunnableParallel(
            {
                # temporarily disable guardrail chain to make use of api gateway guardrail
                # guardrail_parallel_chain_key: guardrails_chain,
                llm_parallel_chain_key: RunnableLambda(langgraph_wrapper)
            }
        )

        complete_chain_output = complete_chain.invoke(agent_input, config=config)
        agent_resp: dict[str, Any] = complete_chain_output.get(
            llm_parallel_chain_key, {}
        )

        multi_agent_structured_resp = {}
        single_agent_structured_resp = {}
        if typed_input.agent_config.agent_type == AgentType.multi_agent:
            multi_agent_structured_resp = {
                "structured_response": AgentState(
                    messages=agent_resp.get("messages"),
                    category=agent_resp.get("category"),
                    expected_category=agent_resp.get("expected_category"),
                    sources=agent_resp.get("sources"),
                    able_to_answer=agent_resp.get("able_to_answer"),
                    answer_confidence_scores=agent_resp.get("answer_confidence_scores"),
                ),
                "agent_actions": agent_resp.get("agent_actions"),
            }
        elif typed_input.agent_config.agent_type in {AgentType.follow_up_convo_agent, AgentType.react_agent}:
            single_agent_structured_resp = {
                "structured_response": SingleAgentState(
                    messages=agent_resp.get("messages"),
                    sources=agent_resp.get("sources"),
                ),
                "agent_actions": agent_resp.get("agent_actions"),
            }

        return (
            {
                "output": agent_resp["messages"][
                    len(agent_resp["messages"]) - 1
                ].content,
            }
            | multi_agent_structured_resp
            | single_agent_structured_resp
        )

    def _get_guardrails_chain(
        self, typed_input: ZionAgentInput
    ) -> RunnableSerializable[Any, dict[str, Any]]:
        if typed_input.agent_config.trigger_guardrails:
            system_prompt, _ = self._get_system_prompt(typed_input)
            guardrail = Guardrail(
                grabgpt_env=global_config.environment,
                api_key=global_config.openai_api_key,
                yaml_content=guardrails_yaml_content,
                enabled_rails=["input"],
                system_prompt=system_prompt,
            )
            return RunnablePassthrough() | RunnableLambda(
                guardrail.runnable_validate_input
            )

        return {}

    async def _handle_ainvoke_react_agent(
        self,
        agent_input: ZionAgentInput,
        agent: AgentExecutor | Pregel,
        config: ZionRunnableConfig | None = None,
    ) -> AsyncGenerator[ZionAgentOutput]:
        # handle for react agent streaming
        async for event in agent.astream_events(
            input=convert_input_to_react_agent_message_dict(agent_input),
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")

            # only return even where the model is streaming
            if kind != "on_chat_model_stream":
                continue
            data = event["data"]
            chunk_content = data.get("chunk", None)
            if not chunk_content or not chunk_content.content:
                continue

            # Empty content in the context of OpenAI or Anthropic usually means
            # that the model is asking for a tool to be invoked.
            # So we only yield non-empty content
            yield {
                "output": ZionAgentOutput(
                    output=chunk_content.content,
                    langsmith_run_id=event.get("run_id", ""),
                )
            }

    async def _load_mcp_tools(self, mcp_servers: dict[str, Any]) -> list:
        """Load MCP tools asynchronously."""
        try:
            mcp_client = MultiServerMCPClient(mcp_servers)
            return await mcp_client.get_tools()
        except (
            Exception  # noqa: BLE001, because we want to handle it gracefully
        ) as e:
            logger.error(f"Failed to load MCP tools: {e}")
            return []

    def invoke(  # noqa: C901, PLR0912
        self: ZionAgent,
        agent_input: dict,
        config: ZionRunnableConfig | None = None,
    ) -> ZionAgentOutput:
        agent_input = self._before_invoke(config=config, agent_input=agent_input)

        typed_input = ZionAgentInput(**agent_input)

        agent: ZionAgent | Pregel
        if typed_input.agent_config.agent_type == AgentType.react_agent:
            agent = self._get_react_agent(typed_input)
        elif typed_input.agent_config.agent_type == AgentType.multi_agent:
            agent = self._get_multi_agent(typed_input)
        elif typed_input.agent_config.agent_type == AgentType.follow_up_convo_agent:
            agent = self._get_follow_up_convo_agent(typed_input)
        else:
            agent = self._get_agent_executor(typed_input, config)

        agent_actions: list[ZionAgentActions] = []
        trail_record: AgentExecutionTrail = None
        tracing_tags = None
        tracer = None

        if (
            typed_input.agent_config.tracing is not None
            and typed_input.agent_config.tracing.tags
        ):
            tracing_tags = typed_input.agent_config.tracing.tags

        try:
            if is_langsmith_enabled():
                with tracing_v2_enabled(
                    project_name=self.agent_profile.langchain_project,
                    client=self._get_langsmith_client(typed_input),
                    tags=tracing_tags,
                ) as tracer:
                    invoke_res = self._handle_invoke_agent(
                        agent=agent,
                        agent_input=agent_input,
                        config=config,
                        tags=tracing_tags,
                    )

                    if "intermediate_steps" in invoke_res:
                        agent_actions = get_zion_agent_actions(
                            invoke_res["intermediate_steps"]
                        )
                        invoke_res["agent_actions"] = agent_actions

            else:
                invoke_res = self._handle_invoke_agent(
                    agent=agent,
                    agent_input=agent_input,
                    config=config,
                )
        except (KeyError, NotFoundError, BadRequestError) as e:
            # Handle OpenAI API errors
            raise HTTPException(status_code=400, detail=e.args[0]) from e
        except HTTPException:
            raise
        except Exception as e:  # , because we want to handle it gracefully
            logger.error("[AGENT_INVOKE_ERROR]", tags={"err": str(e)})
            raise HTTPException(status_code=500, detail=str(e)) from e
        else:
            trail_record = self._log_trail(tracer=tracer, agent_actions=agent_actions)
            if trail_record:
                invoke_res["agent_execution_trail_id"] = trail_record.id
                invoke_res["langsmith_run_id"] = trail_record.langsmith_run_id.__str__()

            return invoke_res

    async def astream(
        self: ZionAgent,
        agent_input: dict,
        config: ZionRunnableConfig | None = None,
    ) -> AsyncIterator[ZionAgentOutput]:
        agent_input = self._before_invoke(config=config, agent_input=agent_input)

        try:
            typed_input = ZionAgentInput(**agent_input)

            agent: ZionAgent | Pregel
            agent = self._get_react_agent(typed_input)
            if typed_input.agent_config.agent_type == AgentType.react_agent:
                try:
                    complete_chain = RunnableParallel(
                        {
                            # guardrail_parallel_chain_key: guardrails_chain,
                            # temporarily disable guardrail chain to make use of api gateway guardrail
                            llm_parallel_chain_key: lambda agent_input: agent.invoke(
                                input=convert_input_to_react_agent_message_dict(
                                    ZionAgentInput(**agent_input)
                                ),
                                config=config,
                            ),
                        }
                    )
                    await complete_chain.ainvoke(agent_input, config=config)

                    async for event in self._handle_ainvoke_react_agent(
                        agent_input=typed_input,
                        agent=self._get_react_agent(typed_input),
                        config=config,
                    ):
                        yield event
                    return  # noqa: TRY300
                except HTTPException:
                    yield {"output": {"output": guardrails_error_message}}
                    return

            # for agent executor streaming by events
            agent = self._get_agent_executor(typed_input, config)

            complete_chain = RunnableParallel(
                {
                    # temporarily disable guardrail chain to make use of api gateway guardrail
                    # guardrail_parallel_chain_key: guardrails_chain,
                    llm_parallel_chain_key: agent,
                }
            )
            complete_chain_output = await complete_chain.ainvoke(
                agent_input, config=config
            )
            yield complete_chain_output.get(llm_parallel_chain_key, {})
        except HTTPException:
            yield {"output": guardrails_error_message}
            return
        except Exception as e:  # , because we want to handle it gracefully
            logger.error("[AGENT_INVOKE_ERROR]", tags={"err": str(e)})
            raise HTTPException(status_code=500, detail=str(e)) from e
