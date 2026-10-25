from app.core.config import get_settings

def test_get_settings_returns_same_instance() -> None:
    assert get_settings() is get_settings() 

def test_settings_has_defaults() -> None:
    settings = get_settings()
    assert settings.app_mode == "mock"
    assert settings.debug is False