import pytest
from elune import ObjectId
from httpx2 import AsyncClient

pytestmark = pytest.mark.anyio


async def test_create_book(client: AsyncClient, book_data: dict):
    response = await client.post("/books/", json=book_data)
    assert response.status_code == 201
    body = response.json()
    assert {key: body[key] for key in book_data} == book_data
    assert str(ObjectId(body["_id"])) == body["_id"]
    assert "object_id" not in body
    second = await client.post("/books/", json=book_data)
    assert second.json()["_id"] != body["_id"]


@pytest.mark.parametrize("field", ["title", "author", "synopsis"])
async def test_create_book_missing_field(client: AsyncClient, book_data: dict, field: str):
    payload = {key: value for key, value in book_data.items() if key != field}
    assert (await client.post("/books/", json=payload)).status_code == 422


@pytest.mark.parametrize("field", ["title", "author", "synopsis"])
@pytest.mark.parametrize("invalid", [None, 123, [], {}])
async def test_create_book_invalid_field(client: AsyncClient, book_data: dict, field: str, invalid):
    response = await client.post("/books/", json={**book_data, field: invalid})
    assert response.status_code == 422


async def test_create_with_custom_object_id(client: AsyncClient, book_data: dict):
    identifier = str(ObjectId())
    response = await client.post("/books/", json={**book_data, "_id": identifier})
    assert response.status_code == 201
    assert response.json()["_id"] == identifier
    assert (await client.get(f"/books/{identifier}")).json() == response.json()


@pytest.mark.parametrize("identifier", ["custom-id", "066de609-b04a-4b30-b46c-32537c7f1f6e", 123])
async def test_invalid_create_id(client: AsyncClient, book_data: dict, identifier):
    response = await client.post("/books/", json={**book_data, "_id": identifier})
    assert response.status_code == 422


async def test_get_and_list_books(client: AsyncClient, book_data: dict):
    assert (await client.get("/books/")).json() == []
    new_book = (await client.post("/books/", json=book_data)).json()
    response = await client.get(f"/books/{new_book['_id']}")
    assert response.status_code == 200
    assert response.json() == new_book
    assert (await client.get("/books/")).json() == [new_book]


async def test_list_limit(client: AsyncClient, book_data: dict):
    for _ in range(101):
        assert (await client.post("/books/", json=book_data)).status_code == 201
    assert len((await client.get("/books/")).json()) == 100


@pytest.mark.parametrize("changes", [{"title": "New"}, {"title": "Don Quixote"}, {}, {"title": None}])
async def test_update_book(client: AsyncClient, book_data: dict, changes: dict):
    new_book = (await client.post("/books/", json=book_data)).json()
    path = f"/books/{new_book['_id']}"
    response = await client.put(path, json=changes)
    assert response.status_code == 200
    expected = {**new_book, **{key: value for key, value in changes.items() if value is not None}}
    assert response.json() == expected
    assert (await client.get(path)).json() == expected


async def test_update_cannot_change_id(client: AsyncClient, book_data: dict):
    book = (await client.post("/books/", json=book_data)).json()
    path = f"/books/{book['_id']}"
    response = await client.put(path, json={"_id": str(ObjectId()), "title": "New"})
    assert response.status_code == 200
    assert response.json() == {**book, "title": "New"}
    assert (await client.get(path)).json() == response.json()


@pytest.mark.parametrize("changes", [{"title": 123}, {"unknown": True}, {"id": "other"}])
async def test_invalid_update(client: AsyncClient, changes: dict):
    response = await client.put(f"/books/{ObjectId()}", json=changes)
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["unknown", "id", "object_id"])
async def test_extra_create_field(client: AsyncClient, book_data: dict, field: str):
    response = await client.post("/books/", json={**book_data, field: "value"})
    assert response.status_code == 422


@pytest.mark.parametrize("method, payload", [("get", None), ("put", {}), ("put", {"title": "new"}), ("delete", None)])
async def test_missing_book(client: AsyncClient, method: str, payload):
    identifier = str(ObjectId())
    kwargs = {"json": payload} if payload is not None else {}
    response = await client.request(method, f"/books/{identifier}", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": f"Book with ID {identifier} not found"}


@pytest.mark.parametrize("method", ["get", "put", "delete"])
async def test_invalid_path_id(client: AsyncClient, method: str):
    kwargs = {"json": {}} if method == "put" else {}
    assert (await client.request(method, "/books/not-an-object-id", **kwargs)).status_code == 422  # pyright: ignore[reportArgumentType]


async def test_delete_book(client: AsyncClient, book_data: dict):
    book = (await client.post("/books/", json=book_data)).json()
    path = f"/books/{book['_id']}"
    response = await client.delete(path)
    assert response.status_code == 204
    assert response.content == b""
    assert (await client.get(path)).status_code == 404
    assert (await client.delete(path)).status_code == 404


async def test_openapi(client: AsyncClient):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    book_schema = schemas.get("Book-Output", schemas.get("Book"))
    assert "_id" in book_schema["properties"]
    assert schemas["BookUpdate"].get("required", []) == []