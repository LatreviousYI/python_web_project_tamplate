from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import orjson

from utils import log_util, response_utils


def register_error_handlers(app: FastAPI) -> None:
    """
    Register global error handlers for the FastAPI application.

    Args:
        app: The FastAPI application instance
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """
        Handle HTTP exceptions and return standardized error responses.
        """
        log_util.logger.error(f"HTTP error: {exc.detail}")
        log_util.logger.exception(exc)
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=response_utils.ApiResponse(code=exc.status_code, message=detail).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """
        Handle pydantic validation errors and return standardized error responses.
        """
        errors = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")} for e in exc.errors()]
        if errors:
            loc = ".".join(str(x) for x in errors[0]["loc"] if x not in ("body", "query", "path"))
            message = f"{loc}: {errors[0]['msg']}" if loc else errors[0]["msg"]
        else:
            message = "参数校验失败"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_utils.ApiResponse(code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=message, data=errors).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle all unhandled exceptions and return standardized error responses.
        """
        if isinstance(exc, orjson.JSONDecodeError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=response_utils.ApiResponse(code=status.HTTP_400_BAD_REQUEST, message="参数异常,可能不是json格式").model_dump(mode="json"),
            )

        log_util.logger.exception(exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_utils.ApiResponse(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Internal Server Error").model_dump(mode="json"),
        )
