import json
from typing import Any

from langchain.schema import AIMessage, HumanMessage
from langchain_core.documents import Document
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
)
from langchain_core.messages.ai import AIMessageChunk
from langchain_core.messages.base import (
    BaseMessageChunk,
)
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.tracers.context import tracing_v2_enabled

from zion.agent.model import ChatGrabGPT
from zion.config import global_config, is_langsmith_enabled, logger
from zion.tool.document_kb_search_tool import HadesDocumentKBSearch
from zion.tool.get_document_content import GetDocumentContentTool
from zion.tool.gitlab_job_trace_tool import GitlabJobTraceTool
from zion.tool.glean_search import GleanSearchTool
from zion.tool.hades_kb_service import HadesKnowledgeBaseTool
from zion.tool.jira_jql_search_tool import JiraJQLSearch
from zion.tool.universal_search import UniversalSearchTool
from zion.util.gpt import (
    GptDocChain,
    get_model_chunk_size,
    get_model_token_limit,
    get_tiktoken_model_name_chat_gpt,
    split_document,
)


def is_message_gpt_function_call(message: BaseMessageChunk) -> bool:
    """is_message_gpt_function_call checks if the given message is a AI Message Chunk trying to perform function calling"""

    return isinstance(message, AIMessageChunk) and (
        message.additional_kwargs.get("tool_calls", None) is not None
        or message.additional_kwargs.get("tool_call_chunks", None) is not None
    )


def is_message_gpt_function_call_reply(message: BaseMessageChunk) -> bool:
    """is_message_gpt_function_call checks if the given message is a AI Message Chunk trying to perform function calling"""

    return isinstance(message, ToolMessage) and message.content != ""


class OptimizeDocumentResultToken:
    max_token: int
    chat_open_ai: ChatGrabGPT
    optimize_token_chat_open_ai: ChatGrabGPT
    messages: list[BaseMessage]
    gpt_doc_chain: GptDocChain

    # we only summarize file that exceed model token limit by 3000
    max_token_difference_to_optimize: int = 3000

    def __init__(self, chat_open_ai: ChatGrabGPT, max_token: int) -> None:
        self.chat_open_ai = ChatGrabGPT(
            api_key=chat_open_ai.openai_api_key,
            base_url=chat_open_ai.openai_api_base,
            model=chat_open_ai.model_name,
            extra_body={},
        )
        self.optimize_token_chat_open_ai = get_tiktoken_model_name_chat_gpt(
            chat_open_ai
        )
        self.max_token = max_token
        self.gpt_doc_chain = GptDocChain(self.chat_open_ai)

    def convert_dict_to_documents(
        self, document_dict: list[dict[str, Any]]
    ) -> list[Document]:
        return [Document(**doc) for doc in document_dict]

    def get_longest_document(self, documents: list[Document]) -> tuple[Document, int]:
        if len(documents) == 0:
            return None, -1

        longest_document = documents[0]
        longest_document_index = 0
        for index, document in enumerate(documents):
            if len(document.page_content) > len(longest_document.page_content):
                longest_document_index = index
                longest_document = document

        return longest_document, longest_document_index

    def summarize_document(self, document: Document) -> str:
        doc_summarized: str = ""
        if is_langsmith_enabled():
            with tracing_v2_enabled(
                project_name=global_config.langchain_token_opt_project,
            ):
                (
                    doc_summarized,
                    _,
                ) = self.gpt_doc_chain.get_map_reduce_chain().combine_docs(
                    docs=split_document(
                        document=document,
                        chunk_size=get_model_chunk_size(self.chat_open_ai.model_name),
                    ),
                )
        else:
            doc_summarized, _ = self.gpt_doc_chain.get_map_reduce_chain().combine_docs(
                docs=split_document(
                    document=document,
                    chunk_size=get_model_chunk_size(self.chat_open_ai.model_name),
                ),
            )
        return doc_summarized

    def convert_documents_to_dict(
        self, documents: list[Document]
    ) -> list[dict[str, str]]:
        return [document.__dict__ for document in documents]

    def shorten_documents(
        self,
        index: int,
        document_item_collection: list[Document],
        longest_doc_index: int,
        longest_doc: Document,
        message: BaseMessage,
    ) -> None:
        # TODO @yujie.ang: refactor this to be pure function for maintainability
        document_item_collection[
            longest_doc_index
        ].page_content = self.summarize_document(longest_doc)

        message.content = json.dumps(
            self.convert_documents_to_dict(document_item_collection)
        )

        self.messages[index] = message

    def optimize_document_result(
        self, messages: list[BaseMessage]
    ) -> list[BaseMessage]:
        self.messages = messages
        num_tokens = self.optimize_token_chat_open_ai.get_num_tokens_from_messages(
            self.messages
        )
        if (num_tokens - self.max_token) > self.max_token_difference_to_optimize:
            # the document user pass in is too long, we dont perform optimize token
            # GPT will return token limit error in this scenario
            return self.messages
        while num_tokens >= self.max_token:
            for index, message in enumerate(self.messages):
                is_document_result = is_message_document_result(message)

                # check if the message is a function call
                if isinstance(message, ToolMessage):
                    document_item_collection: list[Document] = []
                    if is_document_result:
                        try:
                            message_content = json.loads(message.content)
                            # there is a chance the message-content is still encapsulated in string, if so we unload it
                            if isinstance(message_content, str):
                                message_content = json.loads(message_content)

                            document_item_collection: list[Document] = (
                                self.convert_dict_to_documents(message_content)
                            )
                        except json.JSONDecodeError:
                            logger.exception(
                                "Unable to get document item from search to optimize token with"
                            )
                            continue

                        longest_doc, longest_doc_index = self.get_longest_document(
                            document_item_collection
                        )

                        if longest_doc_index == -1:
                            continue
                    else:
                        # this is an open api plugin output
                        # we simulate it as a document for it to be summarized
                        longest_doc = Document(page_content=message.content)
                        document_item_collection: list[Document] = [longest_doc]
                        longest_doc_index = 0
                    self.shorten_documents(
                        index,
                        document_item_collection,
                        longest_doc_index,
                        longest_doc,
                        message,
                    )

                num_tokens = (
                    self.optimize_token_chat_open_ai.get_num_tokens_from_messages(
                        self.messages
                    )
                )
                if num_tokens < self.max_token:
                    break

        return self.messages


class OptimizeMessageToken:
    """langchain will return conversation with type 'system', as well as function calls, along with user 'chat history', such as humanMessage and aiMessage.
    This class will only focus on optimizing human and ai message (chat history)
    """

    max_token: int
    chat_open_ai: ChatGrabGPT
    optimize_token_chat_open_ai: ChatGrabGPT
    contain_function_call: bool
    max_message_token_percentage: float = 0.2
    messages: list[BaseMessage]

    def __init__(self, chat_open_ai: ChatGrabGPT, max_token: int) -> None:
        self.chat_open_ai = ChatGrabGPT(
            api_key=chat_open_ai.openai_api_key,
            base_url=chat_open_ai.openai_api_base,
            model=chat_open_ai.model_name,
            extra_body={},
        )
        self.optimize_token_chat_open_ai = get_tiktoken_model_name_chat_gpt(
            chat_open_ai
        )
        self.max_token = max_token

    def get_conversation_message(self) -> tuple[list[BaseMessage], int]:
        """To get message with type 'human' and 'ai'.
        This is because langchain will return conversation with type 'system', as well as function calls, along with user 'chat history', such as humanMessage and aiMessage
        """
        new_conversation_message: list[BaseMessage] = []
        start_conversation_index = -1
        for index, message in enumerate(self.messages):
            if is_conversation_message(message):
                if start_conversation_index == -1:
                    start_conversation_index = index
                new_conversation_message.append(message)

        return new_conversation_message, start_conversation_index

    def optimize_message_token(
        self, token_limit: int, messages: list[BaseMessage]
    ) -> list[BaseMessage]:
        """
        iterate through message, add last n messages into message until it is less than token limit
        """
        new_messages: list[BaseMessage] = []
        reversed_messages = reversed(messages)
        for message in reversed_messages:
            new_messages.append(message)
            num_token = self.optimize_token_chat_open_ai.get_num_tokens_from_messages(
                new_messages
            )
            if num_token >= token_limit:
                # remove last element as it exceeded limit
                new_messages.pop()
                break

        return list(reversed(new_messages))

    def get_token_limit_for_message(
        self, conversation_message: list[BaseMessage]
    ) -> int:
        """Get the token limit for chat history between human and ai message"""

        # get the total token count for all messages
        total_token_count = (
            self.optimize_token_chat_open_ai.get_num_tokens_from_messages(self.messages)
        )

        # get the total count for all conversation messages, aka messages with type human and ai
        conversation_message_token_count = (
            self.optimize_token_chat_open_ai.get_num_tokens_from_messages(
                conversation_message
            )
        )
        non_conversation_token_count = (
            total_token_count - conversation_message_token_count
        )
        return self.max_token - non_conversation_token_count

    def generate_new_message(
        self,
        start_conversation_index: int,
        current_conversation_message: list[BaseMessage],
        new_conversation_messages: list[BaseMessage],
    ) -> None:
        """Generate new messages collection
        Remove the old messages with type "human" and "ai", and replace it with the new conversation messages
        """

        # gets the messages collection before the "human" and "ai" conversation
        messages_before_conversation = self.messages[0:start_conversation_index]

        # gets the messages collection after the "human" and "ai" conversation.
        # usually it will be function calling messages
        messages_after_conversation = self.messages[
            start_conversation_index + len(current_conversation_message) :
        ]

        # append the messages before chat history, new chat history conversation messages, and messages after chat history
        self.messages = (
            messages_before_conversation
            + new_conversation_messages
            + messages_after_conversation
        )

    def remove_tool_without_resp(self) -> None:
        """remove_tool_without_resp removes any tool calling that has no response
        This is because langchain has a chance of returning tools that has no tool response
        """
        new_messages: list[BaseMessage] = []
        for index, message in enumerate(self.messages):
            # we check that the index is one spot from the last message

            # need to check if the message is gpt initializing function call
            is_message_gpt_func_call = is_message_gpt_function_call(message)
            next_elem_index = index + 1

            # we check if the func is gpt call
            # and if the next one is not a gpt tool call reply, we ignore the current element

            # we also check if the current element is the last element
            # and the last element is a GPT tool call but has no reply
            if (
                is_message_gpt_func_call
                and next_elem_index <= len(self.messages) - 1
                and (
                    not is_message_gpt_function_call_reply(
                        self.messages[next_elem_index]
                    )
                )
            ) or (index == len(self.messages) - 1 and is_message_gpt_func_call):
                continue

            new_messages.append(message)
        self.messages = new_messages

    def convert_aimessage_for_mcp_tool(
        self, messages: list[BaseMessage]
    ) -> list[BaseMessage]:
        """
        Convert the tool message for mcp tool
        Reason is invoking mcp tool will return "run_manager" and "config", which cannot be JSON serialized
        We can safely delete these args, since they are not needed for LLM Agent to maintain context of the tool call
        """
        new_messages = []
        for message in messages:
            if isinstance(message, AIMessage):
                new_tool_calls = []
                for tool_call in message.tool_calls:
                    args = tool_call["args"]
                    if args.get("run_manager", None) is not None:
                        del args["run_manager"]
                    if args.get("config", None) is not None:
                        del args["config"]
                    tool_call["args"] = args
                    new_tool_calls.append(tool_call)
                new_messages.append(
                    AIMessage(
                        id=message.id,
                        tool_calls=new_tool_calls,
                        additional_kwargs=message.additional_kwargs,
                        content=message.content,
                    )
                )
                continue
            new_messages.append(message)

        return new_messages

    def optimize_token(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Optimize token for chat history between human and ai message.
        This is the main starting function to optimize token for chat history
        """
        self.messages = messages
        self.contain_function_call = is_contain_function_call(self.messages)
        current_conversation_message, start_conversation_index = (
            self.get_conversation_message()
        )

        new_conversation_message: list[BaseMessage] = []

        current_conversation_message = self.convert_aimessage_for_mcp_tool(messages)

        # did not perform search, can use full token limit for message
        token_limit_to_use = self.get_token_limit_for_message(
            current_conversation_message
        )
        # there is a chance the token limit to use returned might be negative
        # if it is negative, we should fallback to use message only within
        # self.max_message_token_percentage% of the token limit
        if self.contain_function_call or token_limit_to_use <= 0:
            # need to optimize between search and conversation
            token_limit_to_use = self.max_token * self.max_message_token_percentage

        new_conversation_message = self.optimize_message_token(
            token_limit_to_use, current_conversation_message
        )
        self.generate_new_message(
            start_conversation_index=start_conversation_index,
            current_conversation_message=current_conversation_message,
            new_conversation_messages=new_conversation_message,
        )

        self.remove_tool_without_resp()

        return self.messages


class OptimizeToken:
    max_token: int
    chat_open_ai: ChatGrabGPT
    optimize_document_result: OptimizeDocumentResultToken
    optimize_message_token: OptimizeMessageToken

    def __init__(self, chat_open_ai: ChatGrabGPT) -> None:
        self.chat_open_ai = ChatGrabGPT(
            api_key=chat_open_ai.openai_api_key,
            base_url=chat_open_ai.openai_api_base,
            model=chat_open_ai.model_name,
            extra_body={},
        )
        self.max_token = get_model_token_limit(self.chat_open_ai.model_name)
        self.optimize_document_result = OptimizeDocumentResultToken(
            chat_open_ai=self.chat_open_ai,
            max_token=self.max_token,
        )
        self.optimize_message_token = OptimizeMessageToken(
            chat_open_ai=self.chat_open_ai,
            max_token=self.max_token,
        )

    def optimize_token(self, prompt: ChatPromptValue) -> ChatPromptValue:
        messages = prompt.to_messages()

        messages = self.optimize_message_token.optimize_token(messages)
        if is_contain_function_call(messages):
            messages = self.optimize_document_result.optimize_document_result(
                messages,
            )

        return ChatPromptValue(messages=messages)


def is_contain_function_call(messages: list[BaseMessage]) -> bool:
    return any(isinstance(message, ToolMessage) for message in messages)


def is_conversation_message(message: BaseMessage) -> bool:
    # check if the message is not ai message chunk
    # this is used by langchain to make function calls
    if isinstance(message, (AIMessageChunk)):
        return False

    return isinstance(message, (AIMessage, HumanMessage))


def is_message_document_result(message: BaseMessage) -> bool:
    tool_to_optimize_message = [
        JiraJQLSearch().name,
        UniversalSearchTool().name,
        GleanSearchTool().name,
        HadesDocumentKBSearch().name,
        GetDocumentContentTool().name,
        GitlabJobTraceTool().name,
        HadesKnowledgeBaseTool().name,
    ]
    return message.additional_kwargs.get(
        "name"
    ) in tool_to_optimize_message or message.name in (tool_to_optimize_message)
