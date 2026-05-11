from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from pypersim_demo.agents.agent import _TOOL_REMINDER, _TOOL_REMINDER_THRESHOLD, _before_model_callback


# --- unit tests ---

def _make_request(n: int) -> MagicMock:
    req = MagicMock()
    req.contents = [MagicMock() for _ in range(n)]
    return req


def test_no_injection_below_threshold():
    req = _make_request(_TOOL_REMINDER_THRESHOLD - 1)
    _before_model_callback(MagicMock(), req)
    assert len(req.contents) == _TOOL_REMINDER_THRESHOLD - 1


def test_injection_at_threshold():
    req = _make_request(_TOOL_REMINDER_THRESHOLD)
    original_last = req.contents[-1]
    _before_model_callback(MagicMock(), req)
    assert len(req.contents) == _TOOL_REMINDER_THRESHOLD + 1
    assert req.contents[-2] is _TOOL_REMINDER
    assert req.contents[-1] is original_last


def test_injection_above_threshold():
    req = _make_request(_TOOL_REMINDER_THRESHOLD + 5)
    original_last = req.contents[-1]
    _before_model_callback(MagicMock(), req)
    assert req.contents[-2] is _TOOL_REMINDER
    assert req.contents[-1] is original_last


def test_no_injection_on_empty_contents():
    req = _make_request(0)
    _before_model_callback(MagicMock(), req)
    assert len(req.contents) == 0


def test_reminder_is_model_role():
    assert _TOOL_REMINDER.role == "model"


# --- integration test ---

class _StaticLlm(BaseLlm):
    """Fake model that always returns a fixed text reply."""

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="Here is a product for you.")],
            ),
            turn_complete=True,
        )


async def _drain(gen: AsyncGenerator) -> None:
    async for _ in gen:
        pass


async def test_reminder_not_accumulated_across_turns():
    """Verify ADK does not persist the injected reminder into session history.

    If ADK stores llm_request.contents verbatim, the reminder would appear
    once more per turn, growing without bound. This test detects that by
    recording how many times the reminder appears in contents on each call.
    """
    captured: list[int] = []  # reminder count per model call

    def _spy_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
        _before_model_callback(callback_context, llm_request)
        count = sum(1 for c in llm_request.contents if c is _TOOL_REMINDER)
        captured.append(count)

    agent = Agent(
        model=_StaticLlm(model="static"),
        name="test_root",
        instruction="You are a test agent.",
        before_model_callback=_spy_callback,
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="test", session_service=session_service)
    await session_service.create_session(app_name="test", user_id="u", session_id="s")

    # Run enough turns to cross the threshold and produce a couple of eligible calls.
    n_turns = (_TOOL_REMINDER_THRESHOLD // 2) + 3
    for _ in range(n_turns):
        msg = types.Content(role="user", parts=[types.Part(text="find me some coffee")])
        await _drain(runner.run_async(user_id="u", session_id="s", new_message=msg))

    eligible = [c for i, c in enumerate(captured) if i >= _TOOL_REMINDER_THRESHOLD // 2]
    assert eligible, "no eligible turns captured — raise n_turns or lower threshold"
    # Each eligible call should inject exactly one reminder, never more.
    assert all(c == 1 for c in eligible), (
        f"reminder accumulated across turns: counts per call = {captured}"
    )
