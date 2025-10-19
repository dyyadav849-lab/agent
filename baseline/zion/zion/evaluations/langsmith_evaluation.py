"""
Core LangSmith evaluation functionality.
This module contains the core evaluation logic that can be used both by
the FastAPI endpoint and the daily evaluation job.
"""

from datetime import datetime
from typing import Optional

import pytz
from langsmith import Client as LangSmithClient
from langsmith.evaluation import evaluate
from llm_evaluation.evaluators import (
    grading_note_evaluator,
    llm_as_judge_evaluator,
    rouge_score_evaluator,
)

from zion.agent.model import GrabGPTChatModelEnum
from zion.agent.zion_agent import ZionAgent
from zion.agent.zion_agent_classes import AgentType, ZionAgentInput
from zion.data.connection import get_session
from zion.evaluations.custom_evaluator import tool_evaluator
from zion.evaluations.db_client import EvaluationDbClient
from zion.evaluations.deepeval_evaluator import (
    contextual_recall_evaluator,
    contextual_relevancy_evaluator,
    faithfulness_evaluator,
)
from zion.evaluations.models import EvaluationResult
from zion.evaluations.util import (
    parse_example_agent_executor,
    parse_example_multi_agent,
)
from zion.logger import get_logger

logger = get_logger(__name__)


class LangSmithEvaluationResult:
    """Result of a LangSmith evaluation"""

    def __init__(  # noqa: PLR0913
        self,
        status: str,
        message: str,
        test_project_name: str,
        test_run_name: str,
        results: Optional[list] = None,
        error: Optional[str] = None,
    ) -> None:
        self.status = status
        self.message = message
        self.test_project_name = test_project_name
        self.test_run_name = test_run_name
        self.results = results or []
        self.error = error


def _process_evaluation_result(  # noqa: C901, PLR0912, PLR0915
    result: dict,
    agent_name: str,
    test_project_name: str,
    experiment_name: str,
    experiment_results: list[dict],
) -> EvaluationResult:
    """Process a single evaluation result and create EvaluationResult object."""
    tool_score = None
    rouge_score = None
    llm_judge_score = None
    grading_note_score = None
    contextual_relevancy_score = None
    llm_judge_comment = None
    grading_note_comment = None
    contextual_relevancy_comment = None
    faithfulness_score = None
    faithfulness_comment = None
    contextual_recall_score = None
    contextual_recall_comment = None

    for eval_result in result["evaluation_results"]["results"]:
        if eval_result.key == "Tools Check":
            tool_score = eval_result.score
        elif "rouge metrics" in eval_result.key:
            rouge_score = eval_result.score
        elif eval_result.key == "llm as judge":
            llm_judge_score = eval_result.score
            llm_judge_comment = eval_result.comment
        elif eval_result.key == "grading note":
            grading_note_score = eval_result.score
            grading_note_comment = eval_result.comment
        elif eval_result.key == "Contextual Relevancy":
            contextual_relevancy_score = eval_result.score
            contextual_relevancy_comment = eval_result.comment
        elif eval_result.key == "Faithfulness":
            faithfulness_score = eval_result.score
            faithfulness_comment = eval_result.comment
        elif eval_result.key == "Contextual Recall":
            contextual_recall_score = eval_result.score
            contextual_recall_comment = eval_result.comment

    actual_output = None
    if hasattr(result["run"], "outputs"):
        actual_output = result["run"].outputs.get("output", "")
    elif hasattr(result["run"], "output"):
        actual_output = result["run"].output

    model_name = None
    channel_name = None
    slack_url = None
    if hasattr(result["run"], "inputs") and result["run"].inputs:
        agent_input = result["run"].inputs.get("agent_input", {})
        if isinstance(agent_input, dict):
            agent_config = agent_input.get("agent_config", {})
            channel_name = agent_input.get("channel_name", "")
            if isinstance(agent_config, dict):
                llm_model = agent_config.get("llm_model", {})
                if isinstance(llm_model, dict):
                    model_name = llm_model.get("model_name")

    # Extract slack_url from example inputs set by data pipeline
    slack_url = None
    if hasattr(result["example"], "inputs") and result["example"].inputs:
        slack_url = result["example"].inputs.get("slack_url")

    # Extract run metadata
    run = result["run"]
    run_name = getattr(run, "name", "")
    run_type = getattr(run, "run_type", "")
    dataset_id = str(result["example"].dataset_id)
    example_id = str(result["example"].id)

    return EvaluationResult(
        agent_name=agent_name,
        test_project_name=test_project_name,
        test_run_name=experiment_results.experiment_name,
        experiment_name=experiment_name,
        run_id=run.id,
        run_name=run_name,
        run_type=run_type,
        model_name=model_name,
        channel_name=channel_name,
        slack_url=slack_url,
        dataset_id=dataset_id,
        example_id=example_id,
        input_text=result["example"].inputs.get("input", ""),
        expected_output=result["example"].outputs.get("expected_output", ""),
        actual_output=actual_output,
        tool_score=tool_score,
        rouge_score=rouge_score,
        llm_judge_score=llm_judge_score,
        grading_note_score=grading_note_score,
        llm_judge_comment=llm_judge_comment,
        grading_note_comment=grading_note_comment,
        contextual_relevancy_score=contextual_relevancy_score,
        contextual_relevancy_comment=contextual_relevancy_comment,
        faithfulness_score=faithfulness_score,
        faithfulness_comment=faithfulness_comment,
        contextual_recall_score=contextual_recall_score,
        contextual_recall_comment=contextual_recall_comment,
    )


async def run_langsmith_evaluation_core(  # noqa: C901, PLR0912, PLR0915
    agent_name: str,
    test_project_name: str,
    agent_input: Optional[dict] = None,
    use_existing_outputs: bool = False,  # noqa: FBT001, FBT002
) -> LangSmithEvaluationResult:
    """
    Core LangSmith evaluation logic that can be used by both the endpoint and daily job.

    Args:
        agent_name: Name of the agent to evaluate
        test_project_name: Name of the test project/dataset in LangSmith
        agent_input: Optional agent configuration input
        use_existing_outputs: Whether to use existing outputs or run agent

    Returns:
        LangSmithEvaluationResult containing the evaluation results
    """
    # Import configuration at the beginning to avoid scope issues
    from zion.config import get_config

    global_config = get_config()

    try:
        logger.info(
            "Starting langsmith evaluation for agent: %s, project: %s",
            agent_name,
            test_project_name,
        )

        agent_type: str = AgentType.agent_executor
        model_name: str = None
        agent_profile = global_config.agent_profiles.get(agent_name, "")
        client = LangSmithClient()
        examples = client.list_examples(dataset_name=test_project_name)

        if agent_input is not None:
            zion_agent_input = ZionAgentInput(input="", **agent_input["input"])
            agent_type = (
                AgentType.agent_executor
                if zion_agent_input.agent_config.agent_type is None
                else zion_agent_input.agent_config.agent_type
            )
            model_name = (
                GrabGPTChatModelEnum.AZURE_GPT4O
                if zion_agent_input.agent_config.llm_model is None
                else zion_agent_input.agent_config.llm_model.model_name
            )
        else:
            model_name = GrabGPTChatModelEnum.AZURE_GPT4O

        # current time will be default to SG timezone
        curr_time = datetime.now(pytz.timezone("Asia/Singapore"))

        # Setup for existing outputs evaluation
        actual_outputs_lookup = {}
        expected_outputs_lookup = {}
        dummy_predictor = None
        agent = None
        test_case_datas = []

        if use_existing_outputs:
            # Extract existing outputs and create lookup for dummy predictor
            for example in examples:
                actual_output = example.outputs.get("actual_output", "")
                expected_output = example.outputs.get("expected_output", "")

                # If not found in direct structure, try nested structure
                if (
                    not actual_output
                    and "output" in example.outputs
                    and isinstance(example.outputs["output"], dict)
                ):
                    output_data = example.outputs["output"]
                    actual_output = output_data.get("actual_output", "")
                    expected_output = output_data.get("expected_output", "")

                # Store outputs in lookup
                input_text = example.inputs.get("input", "")
                actual_outputs_lookup[input_text] = actual_output
                expected_outputs_lookup[input_text] = expected_output

                # Add to test case data
                test_case_datas.append(example)

            def dummy_predictor(inputs: dict) -> dict:
                """Pass-through predictor that returns the pre-existing actual_output"""
                input_text = inputs.get("input", "")
                actual_output = actual_outputs_lookup.get(input_text, "")
                return {"output": actual_output}

            experiment_name = f"existing_dataset_eval_{agent_name}_{global_config.environment}_{model_name}_{curr_time}"
            logger.info(
                "Using existing outputs mode. Experiment name: %s", experiment_name
            )
        else:
            # Normal agent execution mode
            agent = ZionAgent(agent_profile=agent_profile)
            if agent_type == AgentType.multi_agent:
                test_case_datas = [
                    # agent_input gets passed in here
                    parse_example_multi_agent(example, zion_agent_input)
                    for example in examples
                ]
            else:
                test_case_datas = [
                    parse_example_agent_executor(example, zion_agent_input)
                    for example in examples
                ]
            experiment_name = f"{test_project_name}_{global_config.environment}_{agent_type.value}_{model_name}_{curr_time}"
            logger.info("Using live agent mode. Experiment name: %s", experiment_name)

        # Choose predictor based on mode
        predictor = dummy_predictor if use_existing_outputs else agent.invoke

        logger.info("Starting evaluation with experiment_name: %s", experiment_name)
        experiment_results = evaluate(
            predictor,
            data=test_case_datas,
            evaluators=[
                tool_evaluator,
                *rouge_score_evaluator(metrics_attribute_to_include=["recall"]),
                llm_as_judge_evaluator(
                    api_key=global_config.openai_api_key,
                    grabgpt_env=global_config.environment,
                    model_name=model_name,
                ),
                grading_note_evaluator(
                    api_key=global_config.openai_api_key,
                    grabgpt_env=global_config.environment,
                    model_name=model_name,
                ),
                contextual_relevancy_evaluator,
                faithfulness_evaluator,
                contextual_recall_evaluator,
            ],
            experiment_prefix=experiment_name,
            max_concurrency=2,
            client=client,
        )

        logger.info(
            "Evaluation completed. Experiment name: %s, Results count: %d",
            experiment_results.experiment_name,
            len(experiment_results),
        )

        # Store results in database with retry and error handling
        # Get batch size from configuration
        batch_size = global_config.evaluation_batch_size

        logger.info(
            "Starting database insertion for %d evaluation results with batch size %d",
            len(experiment_results),
            batch_size,
        )
        db_client = EvaluationDbClient(get_session)

        inserted_count = 0
        failed_count = 0
        current_batch = []
        total_batches = (len(experiment_results) + batch_size - 1) // batch_size
        current_batch_num = 0

        for i, result in enumerate(experiment_results):
            try:
                evaluation_result = _process_evaluation_result(
                    result,
                    agent_name,
                    test_project_name,
                    experiment_name,
                    experiment_results,
                )
                current_batch.append(evaluation_result)

                # Insert batch when it reaches batch_size or on the last item
                if len(current_batch) >= batch_size or i == len(experiment_results) - 1:
                    current_batch_num += 1
                    try:
                        db_client.insert_evaluation_results_batch(current_batch)
                        inserted_count += len(current_batch)
                        logger.info(
                            "Successfully inserted batch %d/%d (%d-%d/%d evaluation results)",
                            current_batch_num,
                            total_batches,
                            i - len(current_batch) + 2,
                            i + 1,
                            len(experiment_results),
                        )
                    except Exception as batch_error:  # noqa: BLE001
                        # If batch insertion fails, try individual insertions
                        logger.warning(
                            "Batch insertion failed, falling back to individual insertions: %s",
                            str(batch_error),
                        )
                        for individual_result in current_batch:
                            try:
                                db_client.insert_evaluation_result(individual_result)
                                inserted_count += 1
                            except Exception as individual_error:  # noqa: BLE001, PERF203
                                failed_count += 1
                                logger.warning(
                                    "Failed to insert individual evaluation result: %s",
                                    str(individual_error),
                                )

                    # Clear the batch for next iteration
                    current_batch = []

            except Exception as e:  # noqa: BLE001, PERF203
                failed_count += 1
                logger.warning(
                    "Failed to process evaluation result %d/%d: %s",
                    i + 1,
                    len(experiment_results),
                    str(e),
                )
                # Continue with next result instead of failing completely
                continue

        logger.info(
            "Database insertion completed. Inserted: %d/%d evaluation results (failed: %d)",
            inserted_count,
            len(experiment_results),
            failed_count,
        )

        # Convert results to JSON-serializable format
        serializable_results = []
        for r in experiment_results:
            input_text = r["example"].inputs.get("input", "")

            # Handle expected_output based on mode
            if use_existing_outputs:
                expected_output = expected_outputs_lookup.get(input_text, "")
            else:
                expected_output = r["example"].outputs.get("expected_output", "")

            result_dict = {
                "run_id": str(r["run"].id),
                "run_name": r["run"].name,
                "input": input_text,
                "expected_output": expected_output,
                "actual_output": r["run"].outputs.get("output", "")
                if hasattr(r["run"], "outputs")
                else r["run"].output,
                "evaluation_results": {
                    eval_result.key: {
                        "score": eval_result.score,
                        "comment": eval_result.comment,
                    }
                    for eval_result in r["evaluation_results"]["results"]
                },
            }
            serializable_results.append(result_dict)

        message = (
            "Evaluation with existing outputs completed"
            if use_existing_outputs
            else "Test completed"
        )

        logger.info("Langsmith evaluation completed successfully")
        logger.info(
            "Returning experiment name: %s", str(experiment_results.experiment_name)
        )

        return LangSmithEvaluationResult(
            status="completed",
            message=message,
            test_project_name=test_project_name,
            test_run_name=str(experiment_results.experiment_name),
            results=serializable_results,
        )

    except (ValueError, ConnectionError, TimeoutError) as e:
        logger.exception("Error in evaluation")
        return LangSmithEvaluationResult(
            status="error",
            message=str(e),
            test_project_name=test_project_name,
            test_run_name="",
            error=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error in langsmith evaluation")
        return LangSmithEvaluationResult(
            status="error",
            message=f"Unexpected error: {e!s}",
            test_project_name=test_project_name,
            test_run_name="",
            error=str(e),
        )
