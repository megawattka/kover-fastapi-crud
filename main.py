from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from kover import from_uri

from app.config import Settings, get_settings
from app.routes import router as book_router


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        async with await from_uri(settings.mongodb_uri) as client:
            application.state["database"] = client.get_database(settings.db_name)
            try:
                yield
            finally:
                del application.state["database"]

    application = FastAPI(title="Kover Books API", version="0.1.0", lifespan=lifespan)
    application.include_router(book_router, tags=["books"], prefix="/books")

    return application

settings = get_settings()
app = create_app(settings=settings)
