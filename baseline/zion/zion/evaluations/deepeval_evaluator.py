"""
DeepEval Evaluators for Multi-Agent Systems.

This module provides evaluators that extract retrieval context from agent_actions in multi-agent workflows
and use DeepEval metrics to assess various aspects of RAG pipeline performance.
"""

# ruff: noqa: G004, SLF001, N806, BLE001, TRY400, EM102, PERF203, TRY003
import json
from typing import Optional

from deepeval.metrics import (
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase
from langchain_core.runnables import RunnableLambda
from langsmith.evaluation import EvaluationResult, run_evaluator
from langsmith.schemas import Example, Run

from zion.agent.model import ChatGrabGPT, GrabGPTChatModelEnum
from zion.config import get_config
from zion.logger import get_logger

logger = get_logger(__name__)

# Constants
MIN_CONTENT_LENGTH = 10
CONTENT_FIELDS = ["page_content", "content", "text", "document_text"]
RETRIEVAL_TOOLS = [
    "universal_search",
    "glean_search",
    "knowledge_base_search",
    "slack_conversation_tool",
    "rag_document_kb_search",
    "openai_web_search",
    "kibana_log_search",
    "jira_jql_search",
    "gitlab_job_trace",
    "get_document_content",
    "ec2_log_retriever",
    "gitlab_endpoint",
    "glean_listshortcuts",
    "concedo_role_extractor_from_ldap",
]


class DeepEvalGrabGPTModel(DeepEvalBaseLLM):
    """Custom DeepEval model using GrabGPT infrastructure."""

    def __init__(self, model: ChatGrabGPT) -> None:
        self.model = model

    def load_model(self):  # noqa: ANN201
        return self.model

    def generate(self, prompt: str) -> str:
        try:
            chat_model = self.load_model()
            # Use RunnableLambda chain pattern to fix tracing issues
            chain = RunnableLambda(lambda x: x) | chat_model
            result = chain.invoke(prompt)
        except Exception as e:
            logger.error(f"DeepEval model generation failed: {type(e).__name__}: {e!s}")
            raise
        else:
            return result.content

    async def a_generate(self, prompt: str) -> str:
        try:
            chat_model = self.load_model()
            # Use RunnableLambda chain pattern to fix tracing issues
            chain = RunnableLambda(lambda x: x) | chat_model
            res = await chain.ainvoke(prompt)
        except Exception as e:
            logger.error(
                f"DeepEval model async generation failed: {type(e).__name__}: {e!s}"
            )
            raise
        else:
            return res.content

    def get_model_name(self) -> str:
        return "GrabGPT Azure GPT-4o"


class _BaseDeepEvalEvaluator:
    """Base class for DeepEval evaluators with common functionality."""

    @staticmethod
    def _create_grabgpt_model():  # noqa: ANN205
        """Create a DeepEval model using GrabGPT infrastructure."""
        from zion.agent.model import ChatGrabGPT

        global_config = get_config()

        try:
            return DeepEvalGrabGPTModel(
                model=ChatGrabGPT.with_unified_api(
                    grabgpt_env=global_config.environment,
                    api_key=global_config.openai_api_key,
                    model_name=GrabGPTChatModelEnum.AZURE_GPT4O,
                )
            )
        except Exception as e:
            logger.error(f"Failed to create GrabGPT model: {type(e).__name__}: {e!s}")
            logger.error(
                f"Environment: {global_config.environment}, API key configured: {'Yes' if global_config.openai_api_key else 'No'}"
            )
            raise

    @staticmethod
    def _extract_input_output(run: Run, example: Example) -> tuple[str, str]:
        """Extract input and output from run and example."""
        input_text = example.inputs.get("input", "")
        if hasattr(run, "outputs") and run.outputs:
            actual_output = run.outputs.get("output", "")
        else:
            actual_output = getattr(run, "output", "")
        return input_text, actual_output

    @staticmethod
    def _create_test_case(
        input_text: str, actual_output: str, retrieval_context: list[str]
    ) -> LLMTestCase:
        """Create a DeepEval test case with the given parameters."""
        return LLMTestCase(
            input=input_text,
            actual_output=actual_output,
            retrieval_context=retrieval_context,
        )

    @staticmethod
    def _log_debug_info(run: Run) -> None:
        """Log debug information when no retrieval context is found."""
        agent_actions = run.outputs.get("agent_actions", [])

        logger.info("No retrieval context found. Debug info:")
        logger.info(f"- Total agent actions: {len(agent_actions)}")

        # Log first 3 agent actions for debugging
        for i, action in enumerate(agent_actions[:3]):
            try:
                tool_name, _, action_type = _get_tool_info_from_action(action, i)
                output_type = type(
                    getattr(action, "tool_output", None)
                    if hasattr(action, "tool_output")
                    else action.get("tool_output", None)
                ).__name__
                logger.info(
                    f"  Agent Action {i} ({action_type}): {tool_name} -> {output_type}"
                )
            except Exception:
                logger.info(f"  Agent Action {i}: unexpected format: {type(action)}")

    @staticmethod
    def _create_error_result(metric_name: str, error_msg: str) -> EvaluationResult:
        """Create an error evaluation result."""
        return EvaluationResult(
            key=metric_name, score=None, comment=f"Evaluation failed: {error_msg}"
        )

    @staticmethod
    def _create_skip_result(metric_name: str, reason: str) -> EvaluationResult:
        """Create a skip evaluation result."""
        return EvaluationResult(key=metric_name, score=None, comment=reason)

    @staticmethod
    def _handle_evaluation_error(
        metric_name: str, error: Exception
    ) -> EvaluationResult:
        """Handle evaluation errors with user-friendly messages."""
        error_msg = str(error)

        # Handle specific error cases
        if "unicodeencodeerror" in error_msg.lower():
            logger.error(f"{metric_name} failed: Unicode encoding error in API key")
            return _BaseDeepEvalEvaluator._create_error_result(
                metric_name, "API key encoding error"
            )
        if "invalid JSON" in error_msg.lower() or "json" in error_msg.lower():
            logger.error(f"{metric_name} failed: Invalid JSON output")
            return _BaseDeepEvalEvaluator._create_error_result(
                metric_name, "LLM produced invalid JSON output"
            )
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            logger.error(f"{metric_name} failed: Connection error")
            return _BaseDeepEvalEvaluator._create_error_result(
                metric_name, "Connection error"
            )
        if (
            "authentication" in error_msg.lower()
            or "unauthorized" in error_msg.lower()
            or "401" in error_msg
        ):
            logger.error(f"{metric_name} failed: Authentication error")
            return _BaseDeepEvalEvaluator._create_error_result(
                metric_name, "Authentication error"
            )
        logger.error(
            f"{metric_name} failed with error: {type(error).__name__}: {error_msg}"
        )
        return _BaseDeepEvalEvaluator._create_error_result(metric_name, str(error))


def _extract_retrieval_context(run: Run) -> list[str]:
    """Extract retrieval context from agent actions (multi-agent systems)."""

    # Get agent_actions (for multi-agent systems)
    agent_actions = run.outputs.get("agent_actions", [])
    logger.info(f"Processing {len(agent_actions)} agent actions")

    # Extract from agent_actions (multi-agent format)
    retrieval_contexts = _extract_from_agent_actions(agent_actions)

    # Remove duplicates while preserving order
    unique_contexts = _deduplicate_contexts(retrieval_contexts)
    logger.info(f"Extracted {len(unique_contexts)} unique contexts total")
    return unique_contexts


def _is_valid_content(content: str) -> bool:
    """Check if content meets minimum length requirements."""
    return content and len(content.strip()) > MIN_CONTENT_LENGTH


def _deduplicate_contexts(contexts: list[str]) -> list[str]:
    """Remove duplicate contexts while preserving order and filtering by length."""
    seen = set()
    unique_contexts = []
    for context in contexts:
        if context not in seen and _is_valid_content(context):
            seen.add(context)
            unique_contexts.append(context)
    return unique_contexts


def _get_tool_info_from_action(action, i: int) -> tuple[str, str, str]:  # noqa: ANN001
    """Extract tool name and output from an action, handling both object and dict formats."""
    if hasattr(action, "tool") and hasattr(action, "tool_output"):
        tool_name = getattr(action, "tool", "")
        tool_output = getattr(action, "tool_output", "")
        action_type = "object"
    elif isinstance(action, dict):
        tool_name = action.get("tool", "")
        tool_output = action.get("tool_output", "")
        action_type = "dict"
    else:
        raise ValueError(f"Unsupported action format: {type(action)}")

    logger.info(
        f"Agent Action {i} ({action_type}): Tool '{tool_name}' with output type: {type(tool_output)}"
    )
    return tool_name, tool_output, action_type


def _extract_from_agent_actions(agent_actions: list) -> list[str]:
    """Extract retrieval context from agent actions (multi-agent systems)."""
    retrieval_contexts = []

    for i, action in enumerate(agent_actions):
        try:
            tool_name, tool_output, _ = _get_tool_info_from_action(action, i)
            retrieval_contexts.extend(
                _extract_content_from_tool_output(tool_name, tool_output)
            )
        except Exception as e:
            logger.warning(f"Error processing agent action {i}: {e!s}")
            continue

    return retrieval_contexts


def _extract_content_from_dict(doc: dict, source_desc: str) -> Optional[str]:
    """Extract content from a document dictionary using standard field names."""
    for field in CONTENT_FIELDS:
        content = doc.get(field)
        if content:
            content_str = str(content).strip()
            if _is_valid_content(content_str):
                logger.info(
                    f"Added context from {source_desc}: {len(content_str)} chars"
                )
                return content_str

    logger.info(
        f"No usable content in {source_desc}. Available keys: {list(doc.keys())}"
    )
    return None


def _is_retrieval_tool(tool_name: str) -> bool:
    """Check if the tool is a retrieval/search tool that provides context."""
    return any(search_tool in tool_name.lower() for search_tool in RETRIEVAL_TOOLS)


def _extract_content_from_tool_output(tool_name: str, tool_output) -> list[str]:  # noqa: ANN001, PLR0912, C901
    """Extract content from tool output if it's a retrieval tool."""
    if not _is_retrieval_tool(tool_name):
        return []

    logger.info("Found retrieval tool: %s", tool_name)
    retrieval_contexts = []

    # Handle string output
    if isinstance(tool_output, str):
        try:
            parsed_output = json.loads(tool_output)
            logger.info("Parsed JSON output type: %s", type(parsed_output))

            if isinstance(parsed_output, list):
                for doc in parsed_output:
                    if isinstance(doc, dict):
                        content = _extract_content_from_dict(doc, "list doc")
                        if content:
                            retrieval_contexts.append(content)
            elif isinstance(parsed_output, dict):
                content = _extract_content_from_dict(parsed_output, "single dict")
                if content:
                    retrieval_contexts.append(content)
        except (json.JSONDecodeError, TypeError):
            # Treat as raw text if JSON parsing fails
            content_str = str(tool_output).strip()
            if _is_valid_content(content_str):
                retrieval_contexts.append(content_str)
                logger.info("Added raw text context: %s chars", len(content_str))

    # Handle direct dict output
    elif isinstance(tool_output, dict):
        content = _extract_content_from_dict(tool_output, "direct dict")
        if content:
            retrieval_contexts.append(content)

    # Handle other formats
    elif tool_output:
        content_str = str(tool_output).strip()
        if _is_valid_content(content_str):
            retrieval_contexts.append(content_str)
            logger.info("Added other format context: %s chars", len(content_str))

    return retrieval_contexts


@run_evaluator
def contextual_relevancy_evaluator(run: Run, example: Example) -> EvaluationResult:
    """Evaluate contextual relevancy using DeepEval for multi-agent systems."""
    METRIC_NAME = "Contextual Relevancy"

    # Extract required inputs
    input_text, actual_output = _BaseDeepEvalEvaluator._extract_input_output(
        run, example
    )
    retrieval_context = _extract_retrieval_context(run)

    # Skip evaluation if no retrieval context found
    if not retrieval_context:
        _BaseDeepEvalEvaluator._log_debug_info(run)
        return _BaseDeepEvalEvaluator._create_skip_result(
            METRIC_NAME, "No retrieval context found for evaluation"
        )

    # Skip if no input or output
    if not input_text or not actual_output:
        logger.info("Missing input or output for contextual relevancy evaluation")
        return _BaseDeepEvalEvaluator._create_skip_result(
            METRIC_NAME, "Missing input or output for evaluation"
        )

    try:
        logger.info(
            f"Running contextual relevancy evaluation with {len(retrieval_context)} context documents"
        )

        # Create custom DeepEval model using GrabGPT infrastructure
        grabgpt_model = _BaseDeepEvalEvaluator._create_grabgpt_model()

        logger.info(
            f"Using GrabGPT model: {GrabGPTChatModelEnum.AZURE_GPT4O} via {get_config().openai_endpoint}/unified/v1"
        )
        metric = ContextualRelevancyMetric(
            threshold=0.7, model=grabgpt_model, include_reason=True
        )

        # Create test case and run evaluation
        test_case = _BaseDeepEvalEvaluator._create_test_case(
            input_text, actual_output, retrieval_context
        )
        metric.measure(test_case)

        logger.info(f"Contextual relevancy score: {metric.score}")

        return EvaluationResult(
            key=METRIC_NAME,
            score=metric.score,
            comment=metric.reason if hasattr(metric, "reason") else None,
        )

    except Exception as e:
        return _BaseDeepEvalEvaluator._handle_evaluation_error(METRIC_NAME, e)


@run_evaluator
def contextual_recall_evaluator(run: Run, example: Example) -> EvaluationResult:
    """Evaluate contextual recall using DeepEval for multi-agent systems.

    The contextual recall metric measures how well the retrieval system captures
    all relevant information by comparing expected_output with retrieval_context.
    """
    METRIC_NAME = "Contextual Recall"

    # Extract required inputs
    input_text, actual_output = _BaseDeepEvalEvaluator._extract_input_output(
        run, example
    )
    retrieval_context = _extract_retrieval_context(run)

    # Get expected output
    expected_output = example.outputs.get("expected_output", "")

    # Skip evaluation if no retrieval context found
    if not retrieval_context:
        _BaseDeepEvalEvaluator._log_debug_info(run)
        return _BaseDeepEvalEvaluator._create_skip_result(
            METRIC_NAME, "No retrieval context found for evaluation"
        )

    # Skip if no expected output (required for contextual recall)
    if not expected_output:
        logger.info("Missing expected output for contextual recall evaluation")
        return _BaseDeepEvalEvaluator._create_skip_result(
            METRIC_NAME, "Missing expected output for evaluation"
        )

    try:
        logger.info(
            f"Running contextual recall evaluation with {len(retrieval_context)} context documents"
        )

        # Create custom DeepEval model using GrabGPT infrastructure
        grabgpt_model = _BaseDeepEvalEvaluator._create_grabgpt_model()

        logger.info(
            f"Using GrabGPT model: {GrabGPTChatModelEnum.AZURE_GPT4O} via {get_config().openai_endpoint}/unified/v1"
        )
        metric = ContextualRecallMetric(
            threshold=0.7, model=grabgpt_model, include_reason=True
        )

        # Create test case and run evaluation
        test_case = LLMTestCase(
            input=input_text,
            actual_output=actual_output,
            expected_output=expected_output,
            retrieval_context=retrieval_context,
        )
        metric.measure(test_case)

        logger.info(f"Contextual recall score: {metric.score}")

        return EvaluationResult(
            key=METRIC_NAME,
            score=metric.score,
            comment=metric.reason if hasattr(metric, "reason") else None,
        )

    except Exception as e:
        return _BaseDeepEvalEvaluator._handle_evaluation_error(METRIC_NAME, e)


@run_evaluator
def faithfulness_evaluator(run: Run, example: Example) -> EvaluationResult:
    """Evaluate faithfulness using DeepEval for multi-agent systems.

    The faithfulness metric measures whether the actual_output factually aligns
    with the contents of the retrieval_context.
    """
    METRIC_NAME = "Faithfulness"

    # Extract required inputs
    input_text, actual_output = _BaseDeepEvalEvaluator._extract_input_output(
        run, example
    )
    retrieval_context = _extract_retrieval_context(run)

    # Skip evaluation if no retrieval context found
    if not retrieval_context:
        _BaseDeepEvalEvaluator._log_debug_info(run)
        return _BaseDeepEvalEvaluator._create_skip_result(
            METRIC_NAME, "No retrieval context found for evaluation"
        )

    # Skip if no input or output
    if not input_text or not actual_output:
        logger.info("Missing input or output for faithfulness evaluation")
        return _BaseDeepEvalEvaluator._create_skip_result(
            METRIC_NAME, "Missing input or output for evaluation"
        )

    try:
        logger.info(
            f"Running faithfulness evaluation with {len(retrieval_context)} context documents"
        )

        # Create custom DeepEval model using GrabGPT infrastructure
        grabgpt_model = _BaseDeepEvalEvaluator._create_grabgpt_model()

        logger.info(
            f"Using GrabGPT model: {GrabGPTChatModelEnum.AZURE_GPT4O} via {get_config().openai_endpoint}/unified/v1"
        )
        metric = FaithfulnessMetric(
            threshold=0.7, model=grabgpt_model, include_reason=True
        )

        # Create test case and run evaluation
        test_case = _BaseDeepEvalEvaluator._create_test_case(
            input_text, actual_output, retrieval_context
        )
        metric.measure(test_case)

        logger.info(f"Faithfulness score: {metric.score}")

        return EvaluationResult(
            key=METRIC_NAME,
            score=metric.score,
            comment=metric.reason if hasattr(metric, "reason") else None,
        )

    except Exception as e:
        return _BaseDeepEvalEvaluator._handle_evaluation_error(METRIC_NAME, e)
