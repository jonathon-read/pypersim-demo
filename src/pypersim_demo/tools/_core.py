from pypersim_demo.db.services import DatabaseServicesError
from pypersim_demo.schemas import ErrorResponse


def error_to_response(error: DatabaseServicesError) -> ErrorResponse:
    return ErrorResponse(error=str(error))
