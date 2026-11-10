import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch):
    for key in ("MONGODB_URI", "DB_NAME"):
        monkeypatch.delenv(key, raising=False)


def test_settings_defaults():
    assert get_settings() == Settings()


def test_settings_field_names():
    settings = Settings(mongodb_uri="mongodb://test:27017/", db_name="test")
    assert settings.mongodb_uri == "mongodb://test:27017/"
    assert settings.db_name == "test"


def test_environment_configuration(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://environment:27017/")
    monkeypatch.setenv("DB_NAME", "environment")
    assert get_settings().mongodb_uri == "mongodb://environment:27017/"
    assert get_settings().db_name == "environment"


def test_legacy_uri_is_not_used(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ATLAS_URI", "mongodb://legacy:27017/")
    assert get_settings() == Settings()


@pytest.mark.parametrize("values", [{"mongodb_uri": "https://localhost"}, {"db_name": ""}, {"unknown": "value"}])
def test_invalid_settings(values: dict):
    with pytest.raises(ValidationError):
        Settings.model_validate(values)