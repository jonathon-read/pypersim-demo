from unittest.mock import MagicMock

import pytest

from pypersim_demo.context import AppContext
from pypersim_demo.db.services import DatabaseServicesError
from pypersim_demo.tools._core import error_to_response, make_tool_registry


def _make_ctx():
    return MagicMock(spec=AppContext)


# --- make_tool_registry ---


def test_tool_factory_registers_and_builds():
    tool_factory, build_registered_tools = make_tool_registry()
    ctx = _make_ctx()

    @tool_factory
    def my_tool(c):
        def inner():
            pass

        inner.__name__ = "my_tool"
        return inner

    tools = build_registered_tools(ctx)
    assert "my_tool" in tools
    assert callable(tools["my_tool"])


def test_tool_factory_passes_context_to_factory():
    tool_factory, build_registered_tools = make_tool_registry()
    ctx = _make_ctx()
    received = []

    @tool_factory
    def capturing_tool(c):
        received.append(c)

        def inner():
            pass

        inner.__name__ = "capturing_tool"
        return inner

    build_registered_tools(ctx)
    assert received == [ctx]


def test_build_registered_tools_returns_all_registered():
    tool_factory, build_registered_tools = make_tool_registry()
    ctx = _make_ctx()

    for name in ("tool_a", "tool_b", "tool_c"):

        def make_factory(n):
            @tool_factory
            def factory(c):
                def inner():
                    pass

                inner.__name__ = n
                return inner

            return factory

        make_factory(name)

    tools = build_registered_tools(ctx)
    assert set(tools) == {"tool_a", "tool_b", "tool_c"}


def test_each_call_to_make_tool_registry_is_independent():
    tool_factory_a, build_a = make_tool_registry()
    tool_factory_b, build_b = make_tool_registry()
    ctx = _make_ctx()

    @tool_factory_a
    def only_in_a(c):
        def inner():
            pass

        inner.__name__ = "only_in_a"
        return inner

    assert "only_in_a" in build_a(ctx)
    assert "only_in_a" not in build_b(ctx)


def test_build_registered_tools_empty_registry():
    _, build_registered_tools = make_tool_registry()
    assert build_registered_tools(_make_ctx()) == {}


# --- error_to_response ---


def test_error_to_response_preserves_message():
    err = DatabaseServicesError(code="DB_ERROR", message="connection refused")
    assert error_to_response(err).error == "connection refused"


def test_error_to_response_returns_error_response():
    from pypersim_demo.schemas import ErrorResponse

    err = DatabaseServicesError(code="X", message="y")
    assert isinstance(error_to_response(err), ErrorResponse)
