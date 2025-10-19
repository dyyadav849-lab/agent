"""Chat implementation of the GrabGPT supported models."""

import os
from collections.abc import Sequence
from enum import StrEnum
from typing import Any, Optional

from langchain_community.tools import BaseTool
from langchain_openai import ChatOpenAI
from llm_kit.constant import Environment


class GrabGPTEnum(StrEnum):
    """Constant for GrabGPT."""

    ENDPOINT_TYPE_PUBLIC = "public"
    """For Tier 2, 3, and 4 data, metadata, request and response are stored"""
    ENDPOINT_TYPE_PRIVATE = "private"
    """For Tier 1 data, only metadata is stored"""

    STG_PUBLIC_ENDPOINT = (
        "https://public-api.grabgpt.managed.catwalk-k8s.stg-myteksi.com"
    )
    """The public endpoint for the GrabGPT STG environment. (Can be accessed via OneVPN directly)"""
    PROD_PUBLIC_ENDPOINT = "https://public-api.grabgpt.managed.catwalk-k8s.myteksi.net"
    """The public endpoint for the GrabGPT PROD environment."""
    STG_PRIVATE_ENDPOINT = (
        "https://private-api.grabgpt.managed.catwalk-k8s.stg-myteksi.com"
    )
    """The private endpoint for the GrabGPT STG environment. (Can be accessed via OneVPN directly)"""
    PROD_PRIVATE_ENDPOINT = (
        "https://private-api.grabgpt.managed.catwalk-k8s.myteksi.net"
    )
    """The private endpoint for the GrabGPT PROD environment."""

    UNIFIED_ENDPOINT_V1 = "/unified/v1/"


class GrabGPTChatModelEnum(StrEnum):
    """
    The list of models supported by GrabGPT's unified LLM API.

    Learn more:
    https://helix.engtools.net/docs/default/component/integrating_llm_apps_with_grabgpt_developer_guide/how-to-use-unified-api
    """

    # Azure OpenAI models
    AZURE_GPT4O = "azure/gpt-4o"  # Reserve instance

    # Azure AI Hub models
    AZURE_AI_DEEPSEEK_R1 = "azure_ai/deepseek-r1"

    # OpenAI Enterprise models
    # https://platform.openai.com/docs/models
    OPENAI_GPT_4_1 = "openai/gpt-4.1"
    OPENAI_GPT_4_1_NANO = "openai/gpt-4.1-nano"
    OPENAI_GPT_4_1_MINI = "openai/gpt-4.1-mini"
    OPENAI_GPT4O = "openai/gpt-4o"
    OPENAI_GPT4O_MINI = "openai/gpt-4o-mini"
    OPENAI_O1_PREVIEW = "openai/o1-preview"
    OPENAI_O1_MINI = "openai/o1-mini"
    OPENAI_O1 = "openai/o1"
    OPENAI_O3_MINI = "openai/o3-mini"
    OPENAI_GPT_5 = "openai/gpt-5"

    # AWS Bedrock (Anthropic Claude)
    BEDROCK_CLAUDE_3_HAIKU = "aws/anthropic.claude-3-haiku-20240307-v1:0"
    BEDROCK_CLAUDE_37_SONNET = "aws/us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    BEDROCK_CLAUDE_4_SONNET = "aws/us.anthropic.claude-sonnet-4-20250514-v1:0"
    BEDROCK_CLAUDE_4_OPUS = "aws/us.anthropic.claude-opus-4-20250514-v1:0"

    # Vertex (Google Gemini)
    GEMINI_1_0_PRO_VISION_001 = "google/gemini-1.0-pro-vision-001"
    GEMINI_2_5_PRO = "google/gemini-2.5-pro"
    GEMINI_2_5_FLASH = "google/gemini-2.5-flash"

    # Perplexity
    # Side note: Perplexity AI is still in Beta Release within Grab
    # Usage would require a separate request
    # You may refer to the documentation here: https://helix.engtools.net/docs/default/component/integrating_llm_apps_with_grabgpt_developer_guide/how-to-use-perplexity-ai-api/#beta-release
    LLAMA_SONAR_REASONING_PRO = "perplexity/sonar-reasoning-pro"
    LLAMA_SONAR_PRO = "perplexity/sonar-pro"


_models_not_supporting_function_calling = [
    GrabGPTChatModelEnum.OPENAI_O1_PREVIEW,
    GrabGPTChatModelEnum.OPENAI_O1_MINI,
    GrabGPTChatModelEnum.OPENAI_O1,
]

_grabgpt_type_env_mapping = {
    GrabGPTEnum.ENDPOINT_TYPE_PUBLIC: {
        Environment.DEV: GrabGPTEnum.STG_PUBLIC_ENDPOINT,
        Environment.STG: GrabGPTEnum.STG_PUBLIC_ENDPOINT,
        Environment.PROD: GrabGPTEnum.PROD_PUBLIC_ENDPOINT,
    },
    GrabGPTEnum.ENDPOINT_TYPE_PRIVATE: {
        Environment.DEV: GrabGPTEnum.STG_PRIVATE_ENDPOINT,
        Environment.STG: GrabGPTEnum.STG_PRIVATE_ENDPOINT,
        Environment.PROD: GrabGPTEnum.PROD_PRIVATE_ENDPOINT,
    },
}


class ChatGrabGPT(ChatOpenAI):
    """
    The chat models class for various models supported by GrabGPT's unified endpoint.

    Includes binding tools to the model, auto detecting if the model supports
    function calling, and setting the base URL and API key for the model.

    Examples:
    ```python
    from llm_kit.langchain.model import ChatGrabGPT, GrabGPTChatModelEnum

    chat_model = ChatGrabGPT.with_unified_api(
        grabgpt_env=app_config.environment,
        model_name=GrabGPTChatModelEnum.AZURE_GPT4O,
        # Pass this if using LangChain tools
        tools=tools,
        # Pass the api key or Set the `GRABGPT_API_KEY` environment variable
        api_key=app_config.grabgpt_api_key,
    )
    # Invoke the GrabGPT models like other LangChain runnables
    invoke_response = chat_model.invoke("Tell me about the history of Large Language Models")
    ...
    invoke_response = chat_model.stream("Tell me about the history of Large Language Models")
    ```

    """

    @staticmethod
    def with_unified_api(  # noqa: PLR0913
        grabgpt_env: str,
        api_key: Optional[str] = None,
        tools: Optional[Sequence[BaseTool]] = None,
        extra_body: Optional[dict[str, Any]] = None,
        endpoint_type: Optional[str] = GrabGPTEnum.ENDPOINT_TYPE_PUBLIC,
        model_name: Optional[str] = GrabGPTChatModelEnum.AZURE_GPT4O,
        timeout: Optional[int] = 120,
        **kwargs: Any,  # noqa: ANN401
    ) -> "ChatGrabGPT":
        """
        Create a ChatGrabGPT instance with specified options.

        Args:
            grabgpt_env (str): The environment for GrabGPT.
            api_key (Optional[str]): The API key for authentication.
            tools (Optional[Sequence[BaseTool]]): Tools to bind with the model.
            extra_body (Optional[dict[str, Any]]): Extra body to be passed along when calling unified endpoint
            endpoint_type (Optional[str]): The endpoint type for the model. Default is public.
            model_name (Optional[str]): The name of the model to use.
            timeout (Optional[int]): The timeout for requests.
            **kwargs: Additional arguments to pass to the constructor.

        Returns:
            ChatGrabGPT: An instance of ChatGrabGPT.

        """
        _grabgpt_env_mapping = _grabgpt_type_env_mapping.get(
            endpoint_type, _grabgpt_type_env_mapping[GrabGPTEnum.ENDPOINT_TYPE_PUBLIC]
        )

        if grabgpt_env not in _grabgpt_env_mapping:
            message = (
                f"Invalid GrabGPT environment: {grabgpt_env}, "
                "must be one of {Environment}"
            )
            raise ValueError(message)

        base_url = _grabgpt_env_mapping[grabgpt_env] + GrabGPTEnum.UNIFIED_ENDPOINT_V1
        if not api_key:
            api_key = os.environ.get("GRABGPT_API_KEY", api_key)

        if not api_key:
            message = (
                "The api_key client option must be set either by passing api_key "
                "to the client or by setting the GRABGPT_API_KEY environment variable"
            )
            raise ValueError(message)

        chat_grabgpt = ChatGrabGPT(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            timeout=timeout,
            extra_body=extra_body,
            **kwargs,
        )

        if not tools or len(tools) == 0:
            return chat_grabgpt

        if not support_function_calling(model_name):
            message = (
                f"Model {model_name} is not supported "
                "for function calling/LangChain tools."
            )
            raise ValueError(message)

        return chat_grabgpt.bind_tools(tools)


def support_function_calling(model_name: str) -> bool:
    """
    Check if the input GrabGPT model supports function calling.

    Args:
        model_name (str): The name of the model to check.

    Returns:
        bool: True if the model supports function calling, False otherwise.

    """
    return model_name not in _models_not_supporting_function_calling
