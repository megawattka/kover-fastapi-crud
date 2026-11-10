from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from kover import Collection

from app.models import Book, BookUpdate
from app.repositories import BookRepository

pytestmark = pytest.mark.anyio


async def test_create_assigns_returned_id_without_mutating_input(book_data: dict):
    collection = MagicMock(spec=Collection)
    identifier = ObjectId()
    collection.insert_one = AsyncMock(return_value=identifier)
    book = Book.model_validate(book_data)
    created = await BookRepository(collection).create(book)
    collection.insert_one.assert_awaited_once_with(book)
    assert book.object_id is None
    assert created.object_id == identifier
    assert created.model_dump(mode="json") == {**book_data, "_id": str(identifier)}


async def test_get_uses_typed_document(book_data: dict):
    collection = MagicMock(spec=Collection)
    identifier = ObjectId()
    book = Book.model_validate({**book_data, "_id": identifier})
    collection.find_one = AsyncMock(side_effect=[book, None])
    repository = BookRepository(collection)
    assert await repository.get(identifier) is book
    collection.find_one.assert_awaited_with({"_id": identifier}, cls=Book)
    assert await repository.get(ObjectId()) is None


async def test_list_uses_typed_cursor_and_closes_it(book_data: dict):
    collection = MagicMock(spec=Collection)
    cursor = collection.find.return_value.limit.return_value
    cursor.__aenter__.return_value = cursor
    books = [Book.model_validate(book_data)]
    cursor.to_list = AsyncMock(return_value=books)
    assert await BookRepository(collection).list(limit=7) == books
    collection.find.assert_called_once_with({}, cls=Book)
    collection.find.return_value.limit.assert_called_once_with(7)
    cursor.to_list.assert_awaited_once()
    cursor.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("changes", [{}, {"title": None}, {"_id": str(ObjectId())}])
async def test_empty_update_does_not_write(book_data: dict, changes: dict):
    collection = MagicMock(spec=Collection)
    collection.update = AsyncMock()
    book = Book.model_validate({**book_data, "_id": ObjectId()})
    collection.find_one = AsyncMock(return_value=book)
    assert book.object_id
    assert await BookRepository(collection).update(book.object_id, BookUpdate.model_validate(changes)) is book
    collection.update.assert_not_awaited()


async def test_update_noop_and_immutable_id(book_data: dict):
    collection = MagicMock(spec=Collection)
    collection.update = AsyncMock(return_value=0)
    book = Book.model_validate({**book_data, "_id": ObjectId()})
    collection.find_one = AsyncMock(return_value=book)
    update = BookUpdate.model_validate({"title": book.title, "_id": ObjectId()})
    repository = BookRepository(collection)
    assert book.object_id
    assert await repository.update(book.object_id, update) is book
    operation = collection.update.await_args.args[0].model_dump()
    assert operation["q"] == {"_id": book.object_id}
    assert operation["u"] == {"$set": {"title": book.title}}
    assert operation["multi"] is False
    collection.find_one.return_value = None
    assert await repository.update(ObjectId(), update) is None


async def test_delete_count():
    collection = MagicMock(spec=Collection)
    collection.delete = AsyncMock(side_effect=[1, 0])
    repository = BookRepository(collection)
    identifier = ObjectId()
    assert await repository.delete(identifier) is True
    assert await repository.delete(identifier) is False
    operation = collection.delete.await_args.args[0].model_dump()
    assert operation["q"] == {"_id": identifier}
    assert operation["limit"] == 1