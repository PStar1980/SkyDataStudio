from scripts import validate


def test_windows_validation_defaults_uv_to_copy_mode(monkeypatch) -> None:
    monkeypatch.setattr(validate.sys, "platform", "win32")
    monkeypatch.delenv("UV_LINK_MODE", raising=False)

    environment = validate.validation_environment()

    assert environment["UV_LINK_MODE"] == "copy"


def test_windows_validation_preserves_explicit_uv_link_mode(monkeypatch) -> None:
    monkeypatch.setattr(validate.sys, "platform", "win32")
    monkeypatch.setenv("UV_LINK_MODE", "clone")

    environment = validate.validation_environment()

    assert environment["UV_LINK_MODE"] == "clone"


def test_non_windows_validation_does_not_invent_uv_link_mode(monkeypatch) -> None:
    monkeypatch.setattr(validate.sys, "platform", "linux")
    monkeypatch.delenv("UV_LINK_MODE", raising=False)

    environment = validate.validation_environment()

    assert "UV_LINK_MODE" not in environment
