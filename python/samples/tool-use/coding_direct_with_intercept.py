"""
This example show case how to intercept the tool execution using
intervention hanlder.
The intervention handler is used to intercept the FunctionCall message
before it is sent out, and prompt the user for permission to execute the tool.
"""

import asyncio
import os
import sys
from typing import Any, List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import FunctionCall
from agnext.components.code_executor import LocalCommandLineCodeExecutor
from agnext.components.models import SystemMessage
from agnext.components.tool_agent import ToolAgent, ToolException
from agnext.components.tools import PythonCodeExecutionTool, Tool
from agnext.core import AgentId, AgentInstantiationContext
from agnext.core.intervention import DefaultInterventionHandler, DropMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from coding_direct import Message, ToolUseAgent
from common.utils import get_chat_completion_client_from_envs


class ToolInterventionHandler(DefaultInterventionHandler):
    async def on_send(self, message: Any, *, sender: AgentId | None, recipient: AgentId) -> Any | type[DropMessage]:
        if isinstance(message, FunctionCall):
            # Request user prompt for tool execution.
            user_input = input(
                f"Function call: {message.name}\nArguments: {message.arguments}\nDo you want to execute the tool? (y/n): "
            )
            if user_input.strip().lower() != "y":
                raise ToolException(content="User denied tool execution.", call_id=message.id)
        return message


async def main() -> None:
    # Create the runtime with the intervention handler.
    runtime = SingleThreadedAgentRuntime(intervention_handler=ToolInterventionHandler())
    # Define the tools.
    tools: List[Tool] = [
        # A tool that executes Python code.
        PythonCodeExecutionTool(
            LocalCommandLineCodeExecutor(),
        )
    ]
    # Register agents.
    await runtime.register(
        "tool_executor_agent",
        lambda: ToolAgent(
            description="Tool Executor Agent",
            tools=tools,
        ),
    )
    await runtime.register(
        "tool_enabled_agent",
        lambda: ToolUseAgent(
            description="Tool Use Agent",
            system_messages=[SystemMessage("You are a helpful AI Assistant. Use your tools to solve problems.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            tool_schema=[tool.schema for tool in tools],
            tool_agent=AgentId("tool_executor_agent", AgentInstantiationContext.current_agent_id().key),
        ),
    )

    run_context = runtime.start()

    # Send a task to the tool user.
    response = await runtime.send_message(
        Message("Run the following Python code: print('Hello, World!')"), AgentId("tool_enabled_agent", "default")
    )
    print(response.content)

    # Run the runtime until the task is completed.
    await run_context.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
