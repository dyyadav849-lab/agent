import json

from langsmith.evaluation import EvaluationResult, run_evaluator
from langsmith.schemas import Example, Run
from typing_extensions import TypedDict

from zion.evaluations.level_zero_test_cases import (
    ZionCategory,
)
from zion.tool.agent_tool import (
    get_zion_agent_actions,
)

python_type_mapping = {
    "str": str,
    "list": list,
    "dict": dict,
    "bool": bool,
    "int": int,
    "float": float,
}


class AgentActionEval(TypedDict, total=False):
    tool_name: str
    expected_call_count: int
    actual_call_count: int | None = 0


@run_evaluator
def must_mention_evaluator(run: Run, example: Example) -> EvaluationResult:
    output = run.outputs.get("output", "").lower()
    must_mention_phrase = (
        example.outputs.get(
            "eval_must_mention",
        )
        or []
    )
    score = all(phrase.lower() in output for phrase in must_mention_phrase)
    return EvaluationResult(key="Must Mention", score=score)


@run_evaluator
def structured_response_type_evaluator(run: Run, example: Example) -> EvaluationResult:
    structured_response = run.outputs.get("structured_response") or {}
    eval_structured_response_type = (
        example.outputs.get(
            "eval_structured_response_type",
        )
        or {}
    )

    score = all(
        output_key in structured_response
        and isinstance(
            structured_response[output_key], python_type_mapping[python_type]
        )
        for output_key, python_type in eval_structured_response_type.items()
    )

    return EvaluationResult(key="Structured Response Type Check", score=score)


@run_evaluator
def structured_response_value_evaluator(run: Run, example: Example) -> EvaluationResult:
    structured_response = run.outputs.get("structured_response", {})
    eval_structured_response_value = (
        example.outputs.get("eval_structured_response_value") or {}
    )
    score = all(
        output_key in structured_response
        and structured_response[output_key] == output_value
        for output_key, output_value in eval_structured_response_value.items()
    )

    return EvaluationResult(key="Structured Response Value Check", score=score)


@run_evaluator
def agent_actions_evaluator(run: Run, example: Example) -> EvaluationResult:
    intermediate_steps = run.outputs.get("intermediate_steps", [])
    agent_actions = get_zion_agent_actions(intermediate_steps)
    agent_action_evals: dict[str, AgentActionEval] = (
        example.outputs.get("eval_agent_actions") or {}
    )

    # set actual_call_count to 0
    for agent_action_eval in agent_action_evals.values():
        if (
            "actual_call_count" not in agent_action_eval
            or agent_action_eval["actual_call_count"] is None
        ):
            agent_action_eval["actual_call_count"] = 0

    for agent_action in agent_actions:
        tool_name = agent_action.tool

        if tool_name in agent_action_evals:
            agent_action_evals[tool_name]["actual_call_count"] += 1

    score = all(
        agent_action_eval["expected_call_count"]
        == agent_action_eval["actual_call_count"]
        for agent_action_eval in agent_action_evals.values()
    )

    return EvaluationResult(key="Agent Actions Check", score=score)


@run_evaluator
def user_query_category_evaluator(run: Run, example: Example) -> EvaluationResult:
    structured_response = run.outputs.get("structured_response", {})
    eval_structured_response_value = (
        example.outputs.get("eval_structured_response_value") or {}
    )

    score = int(
        structured_response["category"] == eval_structured_response_value["category"]
    )

    return EvaluationResult(key="User Query Category Check", score=score)


@run_evaluator
def able_to_answer_user_evaluator(run: Run, example: Example) -> EvaluationResult:
    structured_response = run.outputs.get("structured_response", {})
    eval_structured_response_value = (
        example.outputs.get("eval_structured_response_value") or {}
    )
    score = int(
        structured_response["able_to_answer"]
        == eval_structured_response_value["able_to_answer"]
    )
    return EvaluationResult(key="Able to Answer User Check", score=score)


def should_trigger_mttx(
    category: str,
    able_to_answer: bool,  # noqa: FBT001, because we want to check if it should trigger mttx
) -> bool:
    return not (
        category in [ZionCategory.QUERY.value, ZionCategory.ISSUE.value]
        and able_to_answer
    )


@run_evaluator
def should_trigger_mttx_evaluator(run: Run, example: Example) -> EvaluationResult:
    structured_response = run.outputs.get("structured_response", {})
    eval_structured_response_value = (
        example.outputs.get("eval_structured_response_value") or {}
    )

    actual_should_trigger_mttx = should_trigger_mttx(
        structured_response["category"], structured_response["able_to_answer"]
    )

    eval_should_trigger_mttx = should_trigger_mttx(
        eval_structured_response_value["category"],
        eval_structured_response_value["able_to_answer"],
    )

    score = int(actual_should_trigger_mttx == eval_should_trigger_mttx)

    return EvaluationResult(key="Should Trigger MTTx Check", score=score)


@run_evaluator
def tool_evaluator(run: Run, example: Example) -> EvaluationResult:
    intermediate_steps = run.outputs.get("intermediate_steps", [])
    agent_actions = get_zion_agent_actions(intermediate_steps)
    tools_evals: list[str] = example.outputs.get("eval_tools") or []

    if isinstance(tools_evals, str):
        try:
            tools_evals = json.loads(tools_evals)
        except json.JSONDecodeError:
            tools_evals = []

    score: bool = 0
    num_tools_used = len(tools_evals)
    for agent_action in agent_actions:
        tool_name = agent_action.tool

        if tool_name in tools_evals:
            score += 1

    avg_score = score / num_tools_used if num_tools_used > 0 else 1

    return EvaluationResult(key="Tools Check", score=avg_score)
