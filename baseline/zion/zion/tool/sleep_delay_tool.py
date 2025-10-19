import time
from typing import Any, Optional

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import logger

MAX_SLEEP_DURATION: int = 180


class SleepDelayToolInput(BaseModel):
    sleep_duration: int = Field(
        description=f"the duration to sleep/delay for. The sleep duration must be in 'seconds'. The maximum sleep duration is {MAX_SLEEP_DURATION}"
    )


class SleepDelayTool(BaseTool):
    name: str = "sleep_delay"
    description: str = (
        "Used to perform sleep delay, before performing any furthur actions"
    )
    args_schema: type[BaseModel] = SleepDelayToolInput
    handle_tool_error: bool = True  # handle ToolExceptions

    exceed_sleep_duration_msg: str = (
        f"The maximum sleep duration is {MAX_SLEEP_DURATION} seconds."
    )

    def raise_sleep_exception(self, sleep_exception: str) -> ValueError:
        """Used to raise a sleep exception"""
        raise ValueError(sleep_exception)

    def sleep_delay_tool(self, sleep_duration: int) -> dict[str, Any]:
        """Used to perform sleep delay, before performing any furthur actions"""
        try:
            # check that the duration must not be more than 3 minutes
            if sleep_duration > MAX_SLEEP_DURATION:
                self.raise_sleep_exception(self.exceed_sleep_duration_msg)

            time.sleep(sleep_duration)

        except Exception as e:
            err_message = f"Unable to perform sleep with exception: {e!s}"
            logger.exception(err_message)
            raise ToolException(err_message) from e

        return f"Succesfully sleep for: {sleep_duration} seconds"

    def _run(
        self, sleep_duration: int, _: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Used to perform sleep delay, before performing any furthur actions"""
        return self.sleep_delay_tool(sleep_duration)

    async def _arun(
        self, sleep_duration: int, _: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Used to perform sleep delay, before performing any furthur actions"""
        return self.sleep_delay_tool(sleep_duration)
