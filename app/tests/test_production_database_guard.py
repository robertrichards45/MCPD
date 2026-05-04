import pytest

from app import _database_uri_is_ephemeral, create_app
from app.config import _normalize_database_uri


def test_railway_blocks_ephemeral_sqlite_database(monkeypatch):
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "project-test")
    monkeypatch.setenv("REQUIRE_PERSISTENT_DATABASE", "1")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/app.db")
    with pytest.raises(RuntimeError, match="Unsafe production database configuration"):
        create_app()


def test_railway_allows_postgres_database(monkeypatch):
    assert _database_uri_is_ephemeral("postgresql://user:pass@example.test:5432/mcpd") is False


def test_railway_postgres_url_is_normalized_for_sqlalchemy():
    assert (
        _normalize_database_uri("postgres://user:pass@example.test:5432/mcpd")
        == "postgresql://user:pass@example.test:5432/mcpd"
    )


def test_railway_allows_sqlite_on_mounted_volume(monkeypatch):
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
    assert _database_uri_is_ephemeral("sqlite:////data/app.db") is False
