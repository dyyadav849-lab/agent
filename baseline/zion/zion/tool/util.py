from pathlib import Path

from langchain import hub

from zion.config import global_config, logger


def read_file(file_path: str) -> str:
    path = Path(file_path)
    if path.is_file() and path.suffix == ".txt":
        return path.read_text(encoding="utf-8")

    err_msg = f"File not found or unsupported file type: {file_path}"
    raise ValueError(err_msg)


def _pull_prompt_hub_commit(hub_commit: str) -> str:
    prompt = hub.pull(
        owner_repo_commit=hub_commit,
        api_url=global_config.langchain_endpoint,
        api_key=global_config.langchain_api_key,
    )
    return prompt.template


def get_prompt(
    prompt_hub_commit: str,
    fallback_prompt: str,
) -> str:
    try:
        return _pull_prompt_hub_commit(
            hub_commit=global_config.langsmith_handle_prefix + "/" + prompt_hub_commit
        )

    except (
        Exception  # noqa: BLE001, because we want to handle it gracefully
    ) as e:
        logger.error(
            f"[_get_{prompt_hub_commit}_prompt] Unable to get hub commit, fallback to default prompts",
            tags={"err": str(e)},
        )

    return fallback_prompt
