import logging
import time

from fastapi import FastAPI, Request, Response, HTTPException
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import Config


app_logger = logging.getLogger("app")
access_logger = logging.getLogger("access")


class AccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)
        request_time = time.perf_counter() - started_at

        status_code = response.status_code

        access_logger.info(
            f"{request.method}:{request.url} STATUS={status_code} TIME({request_time})"
        )
        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            return await call_next(request)
        except HTTPException as e:
            raise e
        except Exception as e:
            app_logger.exception(msg=f"Caught unhandled {e.__class__} exception: {e}")
            return Response("Internal Server Error", status_code=500)


def add_middlewares(app: FastAPI) -> None:
    # do not change order
    # app.add_middleware(ExceptionHandlerMiddleware)
    # app.add_middleware(AccessMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=Config.ORIGINS,
        allow_credentials=True,
        allow_methods=["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"],
        allow_headers=["Content-Type","Set-Cookie", "Authorization"],
    )
