from langchain import hub
from requests import HTTPError

from app.core.config import app_config, logger

BASE_PROMPT_COMMIT = "llm-scaffolding/adversarial-safe-base-prompt"


def get_safe_final_prompt(system_prompt: str) -> str:
    """This function fetches the base prompt from the LangChain Hub and appends the system prompt to it.
    Following links for the base prompt:
    Stg: https://langsmith.cauldron.myteksi.net/hub/llm-scaffolding/adversarial-safe-base-prompt
    Prd: https://langsmith.stg.cauldron.myteksi.net/hub/llm-scaffolding/adversarial-safe-base-prompt

    Args:
        system_prompt (str): System prompt to append to the base prompt

    Returns:
        str: Final prompt to be used for the agent
    """
    try:
        base_prompt = hub.pull(
            owner_repo_commit=BASE_PROMPT_COMMIT,
            api_url=app_config.langchain_endpoint,
        )
        return base_prompt.template + system_prompt
    except HTTPError as e:
        logger.error(
            "Failed to pull base prompt %s, err: %s", BASE_PROMPT_COMMIT, str(e)
        )

    return system_prompt
