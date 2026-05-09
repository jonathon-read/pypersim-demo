import pytest

from pypersim_demo.db.services._errors import DatabaseServicesError


def test_is_exception_subclass():
    assert issubclass(DatabaseServicesError, Exception)


def test_code_attribute():
    exc = DatabaseServicesError(code="NOT_FOUND", message="item missing")
    assert exc.code == "NOT_FOUND"


def test_message_in_args():
    exc = DatabaseServicesError(code="CONFLICT", message="duplicate key")
    assert exc.args[0] == "duplicate key"


def test_str_representation():
    exc = DatabaseServicesError(code="ERR", message="something went wrong")
    assert str(exc) == "something went wrong"


def test_can_be_raised_and_caught():
    with pytest.raises(DatabaseServicesError) as exc_info:
        raise DatabaseServicesError(code="FAIL", message="boom")
    assert exc_info.value.code == "FAIL"
