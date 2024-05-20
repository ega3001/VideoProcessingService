import logging

from fastapi import FastAPI, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.middlewares import add_middlewares
from api.routers import users_router, projects_router, payments_router, languages_router, share_router
from core.admin import init_admin
from core.config import Config

if Config.DEBUG:
    app = FastAPI(title="vpsDub", version="1.0.0")
else:
    app = FastAPI(title="vpsDub", version="1.0.0",
                  docs_url=None, redoc_url=None)

app.include_router(users_router, prefix="/users")
app.include_router(projects_router, prefix="/projects")
app.include_router(payments_router, prefix="/payments")
app.include_router(languages_router, prefix="/languages")
app.include_router(share_router, prefix="/share")

FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

add_middlewares(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=({"detail": str(exc.errors()[0]["msg"])}),
    )


@app.on_event("startup")
async def startup():
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized.")

    if Config.DEBUG:
        init_admin(app)
        logger.info("Admin initialized.")
    else:
        logger.info("Admin disabled.")
