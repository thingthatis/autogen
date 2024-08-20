import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.core import AgentId
from agnext.core.exceptions import MessageDroppedException
from agnext.core.intervention import DefaultInterventionHandler, DropMessage
from test_utils import LoopbackAgent, MessageType


@pytest.mark.asyncio
async def test_intervention_count_messages() -> None:

    class DebugInterventionHandler(DefaultInterventionHandler):
        def __init__(self) -> None:
            self.num_messages = 0

        async def on_send(self, message: MessageType, *, sender: AgentId | None, recipient: AgentId) -> MessageType:
            self.num_messages += 1
            return message

    handler = DebugInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handler=handler)
    await runtime.register("name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    run_context = runtime.start()

    _response = await runtime.send_message(MessageType(), recipient=loopback)

    await run_context.stop()

    assert handler.num_messages == 1
    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 1

@pytest.mark.asyncio
async def test_intervention_drop_send() -> None:

    class DropSendInterventionHandler(DefaultInterventionHandler):
        async def on_send(self, message: MessageType, *, sender: AgentId | None, recipient: AgentId) -> MessageType | type[DropMessage]:
            return DropMessage

    handler = DropSendInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handler=handler)

    await runtime.register("name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    run_context = runtime.start()

    with pytest.raises(MessageDroppedException):
        _response = await runtime.send_message(MessageType(), recipient=loopback)

    await run_context.stop()

    loopback_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert loopback_agent.num_calls == 0


@pytest.mark.asyncio
async def test_intervention_drop_response() -> None:

    class DropResponseInterventionHandler(DefaultInterventionHandler):
        async def on_response(self, message: MessageType, *, sender: AgentId, recipient: AgentId | None) -> MessageType | type[DropMessage]:
            return DropMessage

    handler = DropResponseInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handler=handler)

    await runtime.register("name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    run_context = runtime.start()

    with pytest.raises(MessageDroppedException):
        _response = await runtime.send_message(MessageType(), recipient=loopback)

    await run_context.stop()


@pytest.mark.asyncio
async def test_intervention_raise_exception_on_send() -> None:

    class InterventionException(Exception):
        pass

    class ExceptionInterventionHandler(DefaultInterventionHandler): # type: ignore
        async def on_send(self, message: MessageType, *, sender: AgentId | None, recipient: AgentId) -> MessageType | type[DropMessage]: # type: ignore
            raise InterventionException

    handler = ExceptionInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handler=handler)

    await runtime.register("name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    run_context = runtime.start()

    with pytest.raises(InterventionException):
        _response = await runtime.send_message(MessageType(), recipient=loopback)

    await run_context.stop()

    long_running_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert long_running_agent.num_calls == 0

@pytest.mark.asyncio
async def test_intervention_raise_exception_on_respond() -> None:

    class InterventionException(Exception):
        pass

    class ExceptionInterventionHandler(DefaultInterventionHandler): # type: ignore
        async def on_response(self, message: MessageType, *, sender: AgentId, recipient: AgentId | None) -> MessageType | type[DropMessage]: # type: ignore
            raise InterventionException

    handler = ExceptionInterventionHandler()
    runtime = SingleThreadedAgentRuntime(intervention_handler=handler)

    await runtime.register("name", LoopbackAgent)
    loopback = AgentId("name", key="default")
    run_context = runtime.start()
    with pytest.raises(InterventionException):
        _response = await runtime.send_message(MessageType(), recipient=loopback)

    await run_context.stop()

    long_running_agent = await runtime.try_get_underlying_agent_instance(loopback, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1
