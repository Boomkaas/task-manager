from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str, code: str) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code


class AuthenticationError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class BusinessRuleError(AppError):
    status_code = 409


async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": error.detail, "code": error.code},
    )
