from collections.abc import Callable

from pypersim_demo.context import AppContext
from pypersim_demo.db.services import DatabaseServicesError
from pypersim_demo.schemas import ErrorResponse


def make_tool_registry() -> tuple[
    Callable, Callable[[AppContext], dict[str, Callable]]
]:
    _registry: list[Callable] = []

    def tool_factory(factory_fn):
        _registry.append(factory_fn)
        return factory_fn

    def build_registered_tools(ctx: AppContext) -> dict[str, Callable]:
        fns = [factory_fn(ctx) for factory_fn in _registry]
        return {fn.__name__: fn for fn in fns}

    return tool_factory, build_registered_tools


def error_to_response(error: DatabaseServicesError) -> ErrorResponse:
    return ErrorResponse(error=str(error))
