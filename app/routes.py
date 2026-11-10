from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, status

from .dependencies import BookRepositoryDep
from .models import Book, BookUpdate

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_book(book: Book, repository: BookRepositoryDep) -> Book:
    return await repository.create(book)


@router.get("/", response_model=list[Book])
async def list_books(repository: BookRepositoryDep) -> list[Book]:
    return await repository.list(limit=100)


@router.get("/{book_id}")
async def find_book(book_id: ObjectId, repository: BookRepositoryDep) -> Book:
    book = await repository.get(book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found",
        )
    return book


@router.put("/{book_id}")
async def update_book(book_id: ObjectId, update: BookUpdate, repository: BookRepositoryDep) -> Book:
    updated = await repository.update(book_id, update)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found",
        )
    return updated


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: ObjectId, repository: BookRepositoryDep) -> Response:
    if not await repository.delete(book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
