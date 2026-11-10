import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

load_dotenv()


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    mongodb_uri: str = Field(default="mongodb://127.0.0.1:27017/")
    db_name: str = Field(default="kover_books", min_length=1)

    @field_validator("mongodb_uri")
    @classmethod
    def _validate_mongodb_uri(cls, value: str) -> str:
        if not value.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("Expected a mongodb:// or mongodb+srv:// URI")

        return value


def get_settings() -> Settings:
    fields = (("mongodb_uri", "MONGODB_URI"), ("db_name", "DB_NAME"))
    return Settings.model_validate(
        {
            field: os.environ[variable]
            for field, variable in fields if variable in os.environ
        }
    )