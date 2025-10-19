# ruff: noqa: T201

import asyncio

from langchain_core.messages import AIMessage, HumanMessage
from langserve import RemoteRunnable

chat_history = []
remote_runnable = RemoteRunnable(
    "http://localhost:8000/agent/ti-bot-level-zero", headers={"agent-secret": ""}
)


async def start_ti_bot_chat_stream() -> None:
    while True:
        human = input("Human (Q/q to quit): ")
        if human in {"q", "Q"}:
            print("AI: Bye bye human")
            break

        ai = None
        print("AI: ")
        async for chunk in remote_runnable.astream(
            {
                "input": human,
                "chat_history": chat_history,
                "agent_config": {
                    "plugins": [
                        {"name": "calculator", "type": "common"},
                    ],
                },
            }
        ):
            # Agent Action
            if "actions" in chunk:
                for action in chunk["actions"]:
                    print(
                        f"Calling Tool ```{action['tool']}``` with input ```{action['tool_input']}```"
                    )
            # Observation
            elif "steps" in chunk:
                for step in chunk["steps"]:
                    print(f"Got result: ```{step['observation']}```")
            # Final result
            elif "output" in chunk:
                print(chunk["output"])
                ai = AIMessage(content=chunk["output"])
            else:
                raise ValueError
            print("------")
        msg = HumanMessage(content=human)
        chat_history.extend([msg, ai])
        # save chat history to file
        print("msg: " + msg.content)


asyncio.run(start_ti_bot_chat_stream())
