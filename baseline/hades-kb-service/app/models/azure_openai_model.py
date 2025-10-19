from collections.abc import Sequence
from enum import Enum
from typing import Optional

from langchain_community.tools import BaseTool
from langchain_core.runnables import Runnable
from langchain_core.utils.function_calling import format_tool_to_openai_tool
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from app.core.config import app_config


class GrabGPTOpenAIModel(str, Enum):
    """Refer https://wiki.grab.com/display/MS/Using+GrabGPT+API+for+programmatic+access"""

    GPT35_Turbo = "gpt-35-turbo"
    GPT35_Turbo_16K = "gpt-35-turbo-16k"
    GPT4 = "gpt-4"
    GPT4_32K = "gpt-4-32k"
    GPT4_TURBO = "gpt-4-turbo"
    GPT4_TURBO_VISION = "gpt-4-turbo-vision"
    ADA_002 = "text-embedding-ada-002"

    def __str__(self) -> str:
        return str(self.value)


def get_azure_openai_model(
    model_name: Optional[GrabGPTOpenAIModel] = GrabGPTOpenAIModel.GPT4_32K,
    timeout: Optional[int] = 60,
    tools: Optional[Sequence[BaseTool]] = None,
) -> Runnable:
    """return AzureChatOpenAI model with tools."""

    azure_chat_openai = AzureChatOpenAI(
        azure_endpoint=app_config.grabgpt_endpoint,
        api_version=app_config.grabgpt_openai_api_version,
        api_key=app_config.grabgpt_api_key,
        azure_deployment=model_name.__str__(),
        timeout=timeout,
        streaming=True,
    )

    if not tools:
        return azure_chat_openai

    return azure_chat_openai.bind(
        tools=[format_tool_to_openai_tool(tool) for tool in tools]
    )


def get_azure_openai_embeddings_model(
    model_name: Optional[GrabGPTOpenAIModel] = GrabGPTOpenAIModel.ADA_002,
    timeout: Optional[int] = 300,
) -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_endpoint=app_config.grabgpt_endpoint,
        api_version=app_config.grabgpt_openai_api_version,
        api_key=app_config.grabgpt_api_key,
        azure_deployment=model_name.__str__(),
        timeout=timeout,
    )
