"""Unit tests for configuration and utilities."""
from shared.config import Settings, get_settings, setup_logging


def test_settings_defaults():
    s = Settings()
    assert "reelsmaker" in s.database_url
    assert s.debug is True
    assert s.log_level == "INFO"
    assert s.sql_echo is False
    assert s.s3_bucket == "reelsmaker"


def test_get_settings_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_setup_logging_returns_logger():
    log = setup_logging("test.logger")
    assert log.name == "test.logger"


def test_cors_origins_default():
    s = Settings()
    assert "http://localhost:3000" in s.cors_origins
