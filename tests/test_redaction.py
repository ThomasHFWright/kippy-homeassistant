import json

from custom_components.kippy.api import _redact, _redact_json


def test_redact_json_handles_nested_fields():
    payload = {
        "data": [{"petID": "123", "info": {"auth_token": "abc"}}],
        "auth_token": "def",
    }
    redacted = _redact_json(json.dumps(payload))
    assert '"petID": "***"' in redacted
    assert '"auth_token": "***"' in redacted


def test_redact_handles_nested_fields():
    payload = {"outer": {"app_code": "xyz", "list": [{"auth_token": "abc"}]}}
    redacted = _redact(payload)
    assert redacted["outer"]["app_code"] == "***"
    assert redacted["outer"]["list"][0]["auth_token"] == "***"
