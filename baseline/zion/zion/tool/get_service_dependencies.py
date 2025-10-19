import traceback
from typing import Any, Optional

from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import logger
from zion.util.convert import correct_env
from zion.util.service_mesh import get_service_mesh


class GetServiceDependenciesInput(BaseModel):
    service_name: str = Field(
        description="the service name to get service information."
    )
    env: str = Field(description="the environment.")


class GetServiceDependenciesTool(BaseTool):
    name: str = "get_service_dependencies"
    description: str = """
    Get service upstream and downstream dependencies.
    """
    args_schema: type[BaseModel] = GetServiceDependenciesInput
    handle_tool_error: bool = True
    metadata: Optional[dict[str, Any]] = None

    def _run(self, service_name: str, env: str) -> str:
        """Use the tool."""

        return self.get_service_dependencies(service_name, env)

    async def _arun(self, service_name: str, env: str) -> str:
        """Use the tool asynchronously."""

        return self.get_service_dependencies(service_name, env)

    def get_service_dependencies(self, service_name: str, env: str) -> str:
        """Get service upstream and downstream dependencies"""
        env = correct_env(env)
        if env == "prd_stg":
            prd_mesh = get_service_mesh(service_name, "prd")
            stg_mesh = get_service_mesh(service_name, "stg")
            return {"production": prd_mesh, "staging": stg_mesh}

        try:
            return get_service_mesh(service_name, env)
        except (ValueError, KeyError, TypeError) as e:
            traceback.print_exc()
            err_message = f"Unable to get service mesh with exception: {e!s}"
            logger.exception(err_message)
            raise ToolException(err_message) from e
