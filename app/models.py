from kover import Document
from pydantic import ConfigDict


class Book(Document):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "title": "Don Quixote",
                "author": "Miguel de Cervantes",
                "synopsis": "Don Quixote is a Spanish novel by Miguel de Cervantes...",
            }
        }
    )

    title: str
    author: str
    synopsis: str


class BookUpdate(Document):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Don Quixote",
                "author": "Miguel de Cervantes",
                "synopsis": "Don Quixote is a Spanish novel by Miguel de Cervantes...",
            }
        }
    )

    title: str | None = None
    author: str | None = None
    synopsis: str | None = None
