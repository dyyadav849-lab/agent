from langchain.chains import (
    LLMChain,
    MapReduceDocumentsChain,
    ReduceDocumentsChain,
    StuffDocumentsChain,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

from zion.agent.model import ChatGrabGPT, GrabGPTChatModelEnum
from zion.config import global_config


def split_document(document: Document, chunk_size: int) -> list[Document]:
    """Split a document into chunks of text. This splitter understands NLP."""
    text_splitter = RecursiveCharacterTextSplitter(
        # number of character of each chunk.
        chunk_size=chunk_size,
    )

    # create an array of doc if the text exceeds the chunk size
    return text_splitter.create_documents([document.page_content])


class GptDocChain:
    chat_open_ai: ChatGrabGPT
    COMBINE_DOCUMENTS_CHAIN_NAME: str = "combine_documents_chain"
    COLLAPSE_DOCUMENTS_CHAIN_NAME: str = "collapse_documents_chain"

    def __init__(self, chat_open_ai: ChatGrabGPT) -> None:
        self.chat_open_ai = chat_open_ai

    def get_stuff_document_chain(
        self, prompt: str, document_variable_name: str, chain_name: str
    ) -> tuple[StuffDocumentsChain, LLMChain]:
        reduce_prompt = PromptTemplate.from_template(prompt)
        reduce_chain = LLMChain(
            llm=self.chat_open_ai, prompt=reduce_prompt, name=chain_name
        )
        stuff_chain = StuffDocumentsChain(
            llm_chain=reduce_chain, document_variable_name=document_variable_name
        )
        return stuff_chain, reduce_chain

    def get_map_reduce_chain(self) -> MapReduceDocumentsChain:
        # the implementation is inspired by the following docs:
        # https://python.langchain.com/docs/use_cases/summarization#option-2.-map-reduce
        document_variable_name = "docs"

        combine_documents_chain, _ = self.get_stuff_document_chain(
            "The following is set of summaries:{docs}\nSummarize this content precisely and concisely, taking into account key points.",
            document_variable_name,
            self.COMBINE_DOCUMENTS_CHAIN_NAME,
        )

        collapse_documents_chain, collapse_llm_chain = self.get_stuff_document_chain(
            "You MUST never use ANY tools for performing this operation.Summarize this content precisely and concisely, taking into account key points: {docs}",
            document_variable_name,
            self.COLLAPSE_DOCUMENTS_CHAIN_NAME,
        )

        # Combines all document into a single summarized document
        # if the document exceeds the token limit, it will collapse/summarize the document before combining them
        reduce_documents_chain = ReduceDocumentsChain(
            combine_documents_chain=combine_documents_chain,
            collapse_documents_chain=collapse_documents_chain,
        )

        # passes all document through a llm chain to summarize it
        # then, combine them into a single summarized document
        return MapReduceDocumentsChain(
            llm_chain=collapse_llm_chain,
            reduce_documents_chain=reduce_documents_chain,
            document_variable_name=document_variable_name,
            return_intermediate_steps=False,
        )


def get_model_token_limit(model_name: str) -> int:
    """Get the token limit for a model. Make room for chat completion return tokens."""
    # Reference: https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo
    # Model reference: https://wiki.grab.com/display/MS/Using+GrabGPT+API+for+programmatic+access
    model_token_limit = {
        GrabGPTChatModelEnum.AZURE_GPT4O: 128000,
    }
    # the default value is 4096
    # this is to accommodate for the model with lowest token, GPT-3 as a fallback
    token_limit = model_token_limit.get(model_name, 4096)
    return int(token_limit * 0.9)


def get_model_chunk_size(model_name: str) -> int:
    # multiply the estimated token availability with 3.2
    # this is because text spliter uses chunk size == character count
    # we estimate that each token is about 3.2 characters
    return get_model_token_limit(model_name) * 3.2


def get_tiktoken_model_name_chat_gpt(chat_grab_gpt: ChatGrabGPT) -> ChatGrabGPT:
    """
    gets the model name without the prefix 'azure' or 'preplexity'.

    Used for getting the actual tiktoken model name for optimize token
    """
    model_name = chat_grab_gpt.model_name
    if "/" in model_name:
        model_name_split = model_name.split("/")

        # remove the first element that has azure
        if len(model_name_split) > 1:
            model_name_split = model_name_split[1:]

        model_name = "/".join(model_name_split)
    chat_grabgpt_data = {
        "api_key": global_config.openai_api_key,
        "base_url": global_config.openai_endpoint,
        "model_name": model_name,
        "temperature": 0,
        "timeout": 300,
    }
    return ChatGrabGPT(model=model_name, **chat_grabgpt_data)
