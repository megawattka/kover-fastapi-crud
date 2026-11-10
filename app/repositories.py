from typing import Protocol

from bson import ObjectId
from kover import Collection, Delete, Update

from .models import Book, BookUpdate


class IBookRepository(Protocol):
    async def create(self, book: Book) -> Book:
        ...

    async def list(self, limit: int = 100) -> list[Book]:
        ...

    async def get(self, book_id: ObjectId) -> Book | None:
        ...

    async def update(self, book_id: ObjectId, book: BookUpdate) -> Book | None:
        ...

    async def delete(self, book_id: ObjectId) -> bool:
        ...


class BookRepository(IBookRepository):
    def __init__(self, collection: Collection) -> None:
        self.collection = collection

    async def create(self, book: Book) -> Book:
        identifier = await self.collection.insert_one(book)
        # Kover returns the assigned ID without mutating the input Document.
        return book.model_copy(update={"object_id": identifier})

    async def list(self, limit: int = 100) -> list[Book]:
        async with self.collection.find({}, cls=Book).limit(limit) as cursor:
            return await cursor.to_list()

    async def get(self, book_id: ObjectId) -> Book | None:
        book = await self.collection.find_one({"_id": book_id}, cls=Book)
        return book

    async def update(self, book_id: ObjectId, update: BookUpdate) -> Book | None:
        changes = update.model_dump(
            exclude={"object_id"}, exclude_unset=True, exclude_none=True
        )
        if changes:
            await self.collection.update(Update({"_id": book_id}, {"$set": changes}))

        # A zero modified count also means a successful no-op update.
        return await self.get(book_id)

    async def delete(self, book_id: ObjectId) -> bool:
        deleted = await self.collection.delete(Delete({"_id": book_id}, limit=1))
        return deleted == 1
