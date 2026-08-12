from unittest.mock import MagicMock

import pytest

from notifications import push

pytestmark = pytest.mark.asyncio


def _subscription(**overrides):
    record = {
        "id": 1,
        "endpoint": "https://push.example.com/abc",
        "p256dh": "p256dh-key",
        "auth_key": "auth-key",
    }
    record.update(overrides)
    return record


async def test_send_push_skips_when_vapid_not_configured(monkeypatch):
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY", "")
    mock_webpush = MagicMock()
    monkeypatch.setattr(push, "webpush", mock_webpush)

    result = await push.send_push(_subscription(), {"title": "hi"})

    assert result is False
    mock_webpush.assert_not_called()


async def test_send_push_passes_ttl_to_webpush(monkeypatch):
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY", "test-private-key")
    mock_webpush = MagicMock()
    monkeypatch.setattr(push, "webpush", mock_webpush)

    result = await push.send_push(_subscription(), {"title": "hi"})

    assert result is True
    mock_webpush.assert_called_once()
    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["ttl"] == push.PUSH_TTL_SECONDS
    assert call_kwargs["ttl"] == 86400


async def test_send_push_custom_ttl_env(monkeypatch):
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY", "test-private-key")
    monkeypatch.setattr(push, "PUSH_TTL_SECONDS", 3600)
    mock_webpush = MagicMock()
    monkeypatch.setattr(push, "webpush", mock_webpush)

    await push.send_push(_subscription(), {"title": "hi"})

    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["ttl"] == 3600


async def test_send_push_stale_subscription_raises(monkeypatch):
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY", "test-private-key")

    response = MagicMock()
    response.status_code = 410
    exc = push.WebPushException("gone", response=response)

    def _raise(*args, **kwargs):
        raise exc

    monkeypatch.setattr(push, "webpush", _raise)

    with pytest.raises(push.StaleSubscription) as exc_info:
        await push.send_push(_subscription(id=42), {"title": "hi"})

    assert exc_info.value.subscription_id == 42


async def test_send_push_other_webpush_exception_returns_false(monkeypatch):
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY", "test-private-key")

    response = MagicMock()
    response.status_code = 500
    exc = push.WebPushException("server error", response=response)

    def _raise(*args, **kwargs):
        raise exc

    monkeypatch.setattr(push, "webpush", _raise)

    result = await push.send_push(_subscription(), {"title": "hi"})

    assert result is False
