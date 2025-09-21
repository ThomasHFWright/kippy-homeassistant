"""Kippy API package exposing the :class:`KippyApi` client."""

from __future__ import annotations

from .client import KippyApi
from ._utils import (
    _decode_json,
    _get_return_code,
    _redact,
    _redact_json,
    _return_code_error,
    _treat_401_as_success,
    _weeks_param,
    _tz_hours,
)

__all__ = [
    "KippyApi",
    "_decode_json",
    "_get_return_code",
    "_redact",
    "_redact_json",
    "_return_code_error",
    "_treat_401_as_success",
    "_weeks_param",
    "_tz_hours",
]
