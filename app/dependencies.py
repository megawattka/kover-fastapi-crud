from typing import Annotated

from fastapi import Depends, Request
from kover import Database

from .repositories import BookRepository


def get_database(request: Request) -> Database:
    return request.app.state["database"]


def get_book_repository(
    database: Annotated[Database, Depends(get_database)],
) -> BookRepository:
    return BookRepository(database.get_collection("books"))


BookRepositoryDep = Annotated[BookRepository, Depends(get_book_repository)]
