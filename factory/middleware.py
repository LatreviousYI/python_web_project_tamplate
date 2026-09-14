from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
import orjson

from utils import log_util, response_utils


def register_error_handlers(app: FastAPI) -> None:
    """
    Register global error handlers for the FastAPI application.

    Args:
        app: The FastAPI application instance
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> Any:
        """
        Handle HTTP exceptions and return standardized error responses.

        Args:
            request: The incoming request
            exc: The raised HTTP exception

        Returns:
            A JSON response with error details
        """
        log_util.logger.error(f"HTTP error: {exc.detail}")
        log_util.logger.exception(exc)
        return response_utils.ApiResponse(code=exc.status_code, message=exc.detail)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> Any:
        """
        Handle all unhandled exceptions and return standardized error responses.

        Args:
            request: The incoming request
            exc: The raised exception

        Returns:
            A JSON response with error details
        """
        if isinstance(exc, orjson.JSONDecodeError):
            return response_utils.ApiResponse(code=status.HTTP_400_BAD_REQUEST, message="参数异常,可能不是json格式")

        return response_utils.ApiResponse(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Internal Server Error")
