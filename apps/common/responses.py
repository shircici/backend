from rest_framework.response import Response


def success_response(data=None, message="success", code=200, status_code=200):
    return Response(
        {
            "code": code,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def error_response(message="error", code=400, data=None, status_code=400):
    return Response(
        {
            "code": code,
            "message": message,
            "data": data,
        },
        status=status_code,
    )
