# pylint: disable=missing-function-docstring

"""Tests for API redaction helpers."""

import json

from custom_components.kippy.api import _redact, _redact_json


def test_redact_json_handles_nested_fields():
    payload = {
        "data": [{"petID": "123", "info": {"app_code": "abc"}}],
        "app_code": "def",
    }
    redacted = _redact_json(json.dumps(payload))
    assert '"petID": "***"' in redacted
    assert '"app_code": "***"' in redacted


def test_redact_handles_nested_fields():
    payload = {"outer": {"app_code": "xyz", "list": [{"petID": "123"}]}}
    redacted = _redact(payload)
    assert redacted["outer"]["app_code"] == "***"
    assert redacted["outer"]["list"][0]["petID"] == "***"
