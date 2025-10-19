from langsmith.evaluation._runner import ExperimentResults

from zion.config import global_config
from zion.evaluations.test_project.ti_bot_level_zero.level_zero_test_cases_handler import (
    LevelZeroAgentTestProject,
)


class AgentNoTestProjectError(ValueError):
    def __init__(self, agent_name: str) -> None:
        super().__init__(f"Agent `{agent_name}` has no test projects configured.")


class InvalidTestProjectNameError(ValueError):
    def __init__(self, test_project_name: str) -> None:
        super().__init__(f"Invalid test project name: {test_project_name}")


test_projects = {
    global_config.agent_profiles["ti-bot-level-zero"].profile_name: {
        LevelZeroAgentTestProject().test_project_name: LevelZeroAgentTestProject
    }
}


def evaluate_agent_test_project(
    agent_name: str, test_project_name: str
) -> ExperimentResults:
    agent_test_projects = test_projects.get(agent_name)
    if agent_test_projects is None:
        raise AgentNoTestProjectError(agent_name)

    test_project = agent_test_projects.get(test_project_name)
    if test_project is None:
        raise InvalidTestProjectNameError(test_project_name)

    return test_project().evaluate()
