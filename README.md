# FastAPI + Pydantic v2 + Kover

An asynchronous book CRUD API built with FastAPI, Pydantic v2, and
[Kover](https://github.com/megawattka/kover), a native async MongoDB driver.

The application uses typed documents, FastAPI dependency injection, and a
repository layer. MongoDB connections are managed through the application
lifespan. Neither PyMongo nor Motor is used.

## Requirements

- Python 3.12 or newer.
- [uv](https://docs.astral.sh/uv/) for dependency management.
- A reachable MongoDB deployment to run the API or integration tests.

## Quick start

Run these commands from the repository root:

```bash
uv sync --dev

# Skip this command if you already have a .env file.
cp .env.example .env

uv run uvicorn main:app --reload
```

The example configuration connects to MongoDB at `127.0.0.1:27017`.
Start MongoDB separately or update the connection URI before launching the API.

Once the server is running:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

## Configuration

Settings are read from environment variables, with `.env` loaded by
`python-dotenv`. Existing environment variables take precedence over `.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017/` | MongoDB connection URI |
| `DB_NAME` | `kover_books` | Database containing the `books` collection |

Example `.env`:

```dotenv
MONGODB_URI=mongodb://127.0.0.1:27017/
DB_NAME=kover_books
```

Use a `mongodb+srv://` URI for deployments such as MongoDB Atlas. The legacy
`ATLAS_URI` variable is not read. Configuration is validated with Pydantic when
the application module is imported; the database connection is opened during
lifespan startup and closed during shutdown.

### BSON dependency

Kover requires the BSON implementation distributed at
https://python.wattka.dev/. The project maps `bson` to a dedicated, explicit uv
index so that other dependencies continue to come from the default index.
Use `uv sync` to install the configured dependency set.

**Do not install PyMongo in the same environment:** it provides the same
`bson` import namespace and can break Kover imports.

## API

| Method | Endpoint | Success response |
| --- | --- | --- |
| `POST` | `/books/` | `201` with the created book |
| `GET` | `/books/` | `200` with up to 100 books |
| `GET` | `/books/{book_id}` | `200` with a single book |
| `PUT` | `/books/{book_id}` | `200` with the updated book |
| `DELETE` | `/books/{book_id}` | `204` with no response body |

### Create a book

```bash
curl --request POST http://127.0.0.1:8000/books/ \
  --header 'Content-Type: application/json' \
  --data '{
    "title": "Don Quixote",
    "author": "Miguel de Cervantes",
    "synopsis": "A Spanish novel about a self-appointed knight."
  }'
```

Example response (the generated `_id` will differ):

```json
{
  "_id": "507f1f77bcf86cd799439011",
  "title": "Don Quixote",
  "author": "Miguel de Cervantes",
  "synopsis": "A Spanish novel about a self-appointed knight."
}
```

### Update a book

Replace the example ID with the `_id` returned when creating a book:

```bash
curl --request PUT http://127.0.0.1:8000/books/507f1f77bcf86cd799439011 \
  --header 'Content-Type: application/json' \
  --data '{"title": "Don Quixote — revised edition"}'
```

### Validation and update behavior

- `title`, `author`, and `synopsis` are required strings when creating a book.
- Models inherit from `kover.Document`. MongoDB stores `_id` as an ObjectId;
  JSON responses represent it as a 24-character hexadecimal string.
- Creation accepts an optional valid `_id`. If omitted, Kover assigns one.
- UUIDs and arbitrary string IDs are not supported. Existing records using
  string UUIDs require a separate data migration.
- `PUT` performs a partial update, not a full replacement. Omitted fields and
  `null` values are ignored.
- An empty update or an update that changes nothing returns `200` if the book
  exists.
- `_id` is immutable. A valid `_id` supplied in an update is ignored.
- Unknown fields and invalid field or ObjectId values return `422`.
- Reading, updating, or deleting a missing book with a valid ID returns `404`.
- Listing is limited to 100 books; no pagination or explicit sort is exposed.

## Architecture and dependency injection

```text
main.py                 Application factory and MongoDB lifespan
app/config.py           Environment loading and validated settings
app/models.py           Book and BookUpdate document models
app/routes.py           Async HTTP handlers
app/dependencies.py     FastAPI dependency providers
app/repositories.py     Repository protocol and Kover implementation
tests/                  HTTP, repository, lifespan, configuration, and integration tests
```

`create_app(settings=...)` constructs an independent application instance.
The lifespan owns the Kover client and exposes its database through application
state. FastAPI resolves the following dependency chain:

```text
get_database → get_book_repository → route handler
```

Handlers receive a repository through `Annotated[..., Depends(...)]` rather
than accessing MongoDB directly. `BookRepository` implements `IBookRepository`
and uses typed Kover reads with `cls=Book`.

## Testing

### Tests without MongoDB

```bash
uv run pytest -q -W error
```

Integration tests are skipped unless explicitly enabled. HTTP tests use an
in-memory repository injected through
`app.dependency_overrides[get_book_repository]`. Repository tests mock Kover
operations, and lifespan tests verify resource cleanup.

HTTP, repository, lifespan, and integration tests run asynchronously using
AnyIO's pytest plugin with the `asyncio` backend. HTTP requests use
`httpx2.AsyncClient` and `ASGITransport`. Lifespan is entered explicitly so that
the application, client, and Kover share the same event loop. Configuration
validation tests remain synchronous.

### Integration tests with MongoDB

Run the complete suite against a local test deployment:

```bash
KOVER_RUN_INTEGRATION=1 \
MONGODB_URI=mongodb://127.0.0.1:27017/ \
uv run pytest -q -W error
```

To run only integration tests, add `-m integration`.

Each integration test creates a database named `kover_books_test_<random>` and
drops it during asynchronous teardown. Tests cover real CRUD operations,
ObjectId handling, immutable IDs, no-op updates, list limits, and concurrent
requests through Kover's connection pool.

**Never point integration tests at production.** The test credentials must
allow creating and dropping the temporary databases.

The GitHub Actions workflow provisions MongoDB 8 and enables integration tests.
