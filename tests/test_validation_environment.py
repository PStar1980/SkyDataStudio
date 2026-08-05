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


def test_development_service_probe_reports_closed_port(monkeypatch) -> None:
    monkeypatch.setattr(validate.socket, "create_connection", _raise_connection_error)

    assert validate.development_service_running(port=5174) is False


def _raise_connection_error(*_args, **_kwargs):
    raise OSError("closed")


def test_development_server_preflight_allows_stopped_services(monkeypatch) -> None:
    monkeypatch.setattr(validate, "api_dev_server_running", lambda: False)
    monkeypatch.setattr(validate, "frontend_dev_server_running", lambda: False)

    validate.ensure_development_servers_stopped()


def test_development_server_preflight_blocks_running_api(monkeypatch) -> None:
    monkeypatch.setattr(validate, "api_dev_server_running", lambda: True)
    monkeypatch.setattr(validate, "frontend_dev_server_running", lambda: False)

    try:
        validate.ensure_development_servers_stopped()
    except RuntimeError as error:
        assert "FastAPI on port 8100" in str(error)
        assert "Stop the API and frontend" in str(error)
    else:
        raise AssertionError("Expected the FastAPI preflight to block validation.")


def test_development_server_preflight_blocks_running_vite(monkeypatch) -> None:
    monkeypatch.setattr(validate, "api_dev_server_running", lambda: False)
    monkeypatch.setattr(validate, "frontend_dev_server_running", lambda: True)

    try:
        validate.ensure_development_servers_stopped()
    except RuntimeError as error:
        assert "Vite on port 5174" in str(error)
        assert "Stop the API and frontend" in str(error)
    else:
        raise AssertionError("Expected the Vite preflight to block validation.")
