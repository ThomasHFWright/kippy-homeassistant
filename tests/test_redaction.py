import importlib.util
import json
import sys
import types
from pathlib import Path

KIPPY_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "kippy"
custom_components = types.ModuleType("custom_components")
sys.modules.setdefault("custom_components", custom_components)
spec = importlib.util.spec_from_file_location(
    "custom_components.kippy.api", KIPPY_DIR / "api.py"
)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
_redact = api._redact
_redact_json = api._redact_json


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
