"""Shared Home Assistant test configuration."""

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):  # pylint: disable=unused-argument
    """Load this checkout through Home Assistant's integration loader."""
