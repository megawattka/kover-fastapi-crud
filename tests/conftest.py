from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from elune import ObjectId
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient

from app.config import Settings
from app.dependencies import get_book_repository
from app.models import Book, BookUpdate
from app.repositories import IBookRepository
from main import create_app


@pytest.fixture
def anyio_backend() -> str:
    # Kover uses native asyncio streams; running it under Trio is not supported.
    return "asyncio"


@pytest.fixture
def book_data() -> dict[str, str]:
    return {
        "title": "Don Quixote",
        "author": "Miguel de Cervantes",
        "synopsis": "...",
    }


class MemoryBookRepository(IBookRepository):
    def __init__(self) -> None:
        self.books: dict[ObjectId, Book] = {}

    async def create(self, book: Book) -> Book:
        identifier = book.object_id if book.object_id is not None else ObjectId()
        stored = book.model_copy(update={"object_id": identifier})
        self.books[identifier] = stored
        return stored

    async def list(self, limit: int = 100) -> list[Book]:
        return list(self.books.values())[:limit]

    async def get(self, book_id: ObjectId) -> Book | None:
        return self.books.get(book_id)

    async def update(self, book_id: ObjectId, book: BookUpdate) -> Book | None:
        existing = self.books.get(book_id)
        if existing is not None:
            self.books[book_id] = existing.model_copy(
                update=book.model_dump(
                    exclude={"object_id"}, exclude_unset=True, exclude_none=True
                )
            )
        return self.books.get(book_id)

    async def delete(self, book_id: ObjectId) -> bool:
        return self.books.pop(book_id, None) is not None


@pytest.fixture
async def client(anyio_backend: str) -> AsyncIterator[AsyncClient]:
    @asynccontextmanager
    async def no_database(application: FastAPI) -> AsyncIterator[None]:
        yield

    application = create_app(Settings())
    application.router.lifespan_context = no_database
    repository = MemoryBookRepository()
    application.dependency_overrides[get_book_repository] = lambda: repository
    try:
        async with application.router.lifespan_context(application):  # noqa: SIM117
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as test_client:
                yield test_client
    finally:
        application.dependency_overrides.clear()