from unittest.mock import AsyncMock, MagicMock

import pytest
from kover import Kover

from app.config import Settings
from main import create_app

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("fail", [False, True])
async def test_lifespan_closes_client(monkeypatch: pytest.MonkeyPatch, fail: bool):
    client = MagicMock(spec=Kover)
    client.close = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)

    async def close_on_exit(*args):
        await client.close()
        return False

    client.__aexit__ = AsyncMock(side_effect=close_on_exit)
    factory = AsyncMock(return_value=client)
    monkeypatch.setattr("main.from_uri", factory)
    application = create_app(Settings(mongodb_uri="mongodb://localhost:27017/", db_name="test_books"))

    async def run_lifespan():
        async with application.router.lifespan_context(application):
            assert application.state["database"] is client.get_database.return_value
            if fail:
                raise RuntimeError("test failure")

    if fail:
        with pytest.raises(RuntimeError, match="test failure"):
            await run_lifespan()
    else:
        await run_lifespan()
    factory.assert_awaited_once_with("mongodb://localhost:27017/")
    client.get_database.assert_called_once_with("test_books")
    client.close.assert_awaited_once()
    assert not hasattr(application.state, "database")