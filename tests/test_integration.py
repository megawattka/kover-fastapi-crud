import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from elune import ObjectId
from httpx2 import ASGITransport, AsyncClient

from app.config import Settings
from main import create_app

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("KOVER_RUN_INTEGRATION") != "1", reason="Set KOVER_RUN_INTEGRATION=1"),
]


@pytest.fixture
async def mongodb_client(anyio_backend: str) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/"),
        db_name=f"kover_books_test_{uuid4().hex}",
    )
    application = create_app(settings)
    # ASGITransport does not run lifespan; keep client, app and Kover on one loop.
    async with application.router.lifespan_context(application):
        try:
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                yield client
        finally:
            await application.state["database"].command({"dropDatabase": 1})
    assert not hasattr(application.state, "database")


async def test_real_mongodb_crud(mongodb_client: AsyncClient, book_data: dict):
    client = mongodb_client
    assert (await client.get("/books/")).json() == []
    response = await client.post("/books/", json=book_data)
    assert response.status_code == 201
    book = response.json()
    assert str(ObjectId(book["_id"])) == book["_id"]
    path = f"/books/{book['_id']}"
    assert (await client.get(path)).json() == book
    assert (await client.get("/books/")).json() == [book]
    for changes in [{"title": "Updated"}, {"title": "Updated"}, {}, {"title": None}, {"_id": str(ObjectId())}]:
        response = await client.put(path, json=changes)
        assert response.status_code == 200
        assert response.json() == {**book, "title": "Updated"}
    # Exercise pool concurrency, unique server IDs and the real cursor limit.
    responses = await asyncio.gather(*(client.post("/books/", json=book_data) for _ in range(101)))
    assert all(response.status_code == 201 for response in responses)
    assert len({response.json()["_id"] for response in responses}) == 101
    assert len((await client.get("/books/")).json()) == 100
    response = await client.delete(path)
    assert response.status_code == 204
    assert response.content == b""
    assert (await client.get(path)).status_code == 404
    assert (await client.put(path, json={"title": "Missing"})).status_code == 404
    assert (await client.put(path, json={})).status_code == 404
    response = await client.delete(path)
    assert response.status_code == 404
    assert response.json() == {"detail": f"Book with ID {book['_id']} not found"}


async def test_real_mongodb_custom_object_id(mongodb_client: AsyncClient, book_data: dict):
    identifier = str(ObjectId())
    response = await mongodb_client.post("/books/", json={**book_data, "_id": identifier})
    assert response.status_code == 201
    assert response.json()["_id"] == identifier
    assert (await mongodb_client.get(f"/books/{identifier}")).json() == response.json()