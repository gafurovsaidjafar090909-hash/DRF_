from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def translated_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        response.data = {"code": "validation_error", "fields": exc.get_codes()}
    elif response.status_code == 401:
        response.data = {"code": "authentication_required"}
    elif response.status_code == 403:
        response.data = {"code": "forbidden"}
    elif response.status_code == 404:
        response.data = {"code": "not_found"}
    return response
