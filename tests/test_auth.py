"""Tests for authentication helpers."""

import importlib

import pytest

from openbrain.utils.errors import AuthenticationError, ConfigurationError


def test_dev_mode_returns_default_user():
    from openbrain.auth.dev_auth import get_current_user

    assert get_current_user() == "dev-user"


def test_static_token_mode_requires_valid_bearer(monkeypatch):
    monkeypatch.setenv("DISABLE_AUTH", "false")
    monkeypatch.setenv("OPENBRAIN_API_TOKEN", "secret-token")

    import openbrain.config as config_module
    import openbrain.auth.dev_auth as auth_module

    importlib.reload(config_module)
    importlib.reload(auth_module)

    assert (
        auth_module.get_current_user({"authorization": "Bearer secret-token"})
        == config_module.Config.DEFAULT_USER_ID
    )

    with pytest.raises(AuthenticationError):
        auth_module.get_current_user({"authorization": "Bearer wrong-token"})

    monkeypatch.setenv("DISABLE_AUTH", "true")
    importlib.reload(config_module)
    importlib.reload(auth_module)


def test_config_requires_static_token_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("DISABLE_AUTH", "false")
    monkeypatch.delenv("OPENBRAIN_API_TOKEN", raising=False)

    import openbrain.config as config_module

    with pytest.raises(ConfigurationError):
        importlib.reload(config_module)

    monkeypatch.setenv("DISABLE_AUTH", "true")
    monkeypatch.setenv("OPENBRAIN_API_TOKEN", "test-token")
    importlib.reload(config_module)
