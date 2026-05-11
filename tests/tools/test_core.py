from pypersim_demo.db.services import DatabaseServicesError
from pypersim_demo.tools._core import error_to_response


def test_error_to_response_preserves_message():
    err = DatabaseServicesError(code="DB_ERROR", message="connection refused")
    assert error_to_response(err).error == "connection refused"


def test_error_to_response_returns_error_response():
    from pypersim_demo.schemas import ErrorResponse

    err = DatabaseServicesError(code="X", message="y")
    assert isinstance(error_to_response(err), ErrorResponse)
