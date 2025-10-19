from fastapi import Request

from zion.config import AgentProfile, global_config


def check_agent_secret(request: Request, agent_name: str) -> AgentProfile:
    """Checks if the given request header contains an agent secret
    Also, checks if the agent secret provided is valid and is defined inside the config
    Returns the agent profile if the agent secret is valid
    """
    agent_profile: AgentProfile = {}
    try:
        agent_profile = global_config.agent_profiles[agent_name]
    except KeyError as e:
        message = f"'{agent_name}' is not a valid agent"
        raise ValueError(message) from e

    if "agent-secret" not in request.headers:
        message = "Agent secret is missing"
        raise ValueError(message)

    if request.headers["agent-secret"] != agent_profile.secret_key:
        message = "Invalid agent secret"
        raise ValueError(message)

    return agent_profile
