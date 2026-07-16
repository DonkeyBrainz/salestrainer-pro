"""Unit tests for logging secret-redaction filter."""

import logging

from app.core.logging import RedactSecretsFilter


def _filtered_message(raw: str) -> str:
    record = logging.LogRecord(
        name="test", level=logging.DEBUG, pathname=__file__, lineno=1,
        msg=raw, args=(), exc_info=None,
    )
    RedactSecretsFilter().filter(record)
    return record.getMessage()


class TestRedactSecretsFilter:
    def test_redacts_goog_api_key_header(self) -> None:
        msg = _filtered_message("> x-goog-api-key: AIzaSyCqUUsk-ezgW6hJH2jLVTNV7LnK3C3iwuM")
        assert "AIzaSyCqUUsk" not in msg
        assert "x-goog-api-key: <redacted>" in msg

    def test_redacts_bearer_token(self) -> None:
        msg = _filtered_message("Authorization: Bearer eyJabc.def.ghi")
        assert "eyJabc" not in msg
        assert "Authorization: Bearer <redacted>" in msg

    def test_redacts_bare_google_api_key_anywhere_in_message(self) -> None:
        msg = _filtered_message("connecting with key=AIzaSyCqUUsk-ezgW6hJH2jLVTNV7LnK3C3iwuM")
        assert "AIzaSyCqUUsk" not in msg
        assert "<redacted>" in msg

    def test_leaves_unrelated_messages_untouched(self) -> None:
        msg = _filtered_message("WebSocket connected")
        assert msg == "WebSocket connected"
