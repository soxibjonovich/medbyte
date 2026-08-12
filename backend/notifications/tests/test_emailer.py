from unittest.mock import AsyncMock

from notifications import emailer


async def test_send_email_skips_when_smtp_not_configured(monkeypatch):
    monkeypatch.setattr(emailer, "SMTP_HOST", "")
    mock_send = AsyncMock()
    monkeypatch.setattr(emailer.aiosmtplib, "send", mock_send)

    result = await emailer.send_email("a@x.com", "hi", "body")

    assert result is False
    mock_send.assert_not_called()


async def test_send_email_success(monkeypatch):
    monkeypatch.setattr(emailer, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(emailer, "SMTP_PORT", 587)
    monkeypatch.setattr(emailer, "SMTP_USER", "u@example.com")
    monkeypatch.setattr(emailer, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(emailer, "SMTP_FROM", "u@example.com")
    mock_send = AsyncMock()
    monkeypatch.setattr(emailer.aiosmtplib, "send", mock_send)

    result = await emailer.send_email("a@x.com", "hi", "body")

    assert result is True
    mock_send.assert_called_once()
    msg = mock_send.call_args.args[0]
    assert msg["To"] == "a@x.com"
    assert msg["From"] == "u@example.com"
    assert msg["Subject"] == "hi"
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["hostname"] == "smtp.example.com"
    assert call_kwargs["port"] == 587
    assert call_kwargs["username"] == "u@example.com"
    assert call_kwargs["password"] == "secret"


async def test_send_email_exception_returns_false(monkeypatch):
    monkeypatch.setattr(emailer, "SMTP_HOST", "smtp.example.com")
    mock_send = AsyncMock(side_effect=OSError("connection refused"))
    monkeypatch.setattr(emailer.aiosmtplib, "send", mock_send)

    result = await emailer.send_email("a@x.com", "hi", "body")

    assert result is False
