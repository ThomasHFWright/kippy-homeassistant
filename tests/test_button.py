from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.kippy.button import (
    KippyActivityCategoriesButton,
    KippyPressButton,
)


@pytest.mark.asyncio
async def test_press_button_calls_api_and_processes_data() -> None:
    """Pressing button triggers API call and processes returned data."""
    coordinator = MagicMock()
    coordinator.api.kippymap_action = AsyncMock(return_value={"ok": True})
    coordinator.process_new_data = MagicMock()
    coordinator.kippy_id = 5
    pet = {"petID": 5, "petName": "Rex"}
    button = KippyPressButton(coordinator, pet)
    await button.async_press()
    coordinator.api.kippymap_action.assert_called_once_with(5)
    coordinator.process_new_data.assert_called_once_with({"ok": True})


@pytest.mark.asyncio
async def test_press_button_propagates_error() -> None:
    """Exceptions from API are not swallowed."""
    coordinator = MagicMock()
    coordinator.api.kippymap_action = AsyncMock(side_effect=RuntimeError)
    coordinator.process_new_data = MagicMock()
    coordinator.kippy_id = 5
    pet = {"petID": 5}
    button = KippyPressButton(coordinator, pet)
    with pytest.raises(RuntimeError):
        await button.async_press()


@pytest.mark.asyncio
async def test_activity_button_refreshes_pet() -> None:
    """Activity button refreshes a single pet."""
    coordinator = MagicMock()
    coordinator.async_refresh_pet = AsyncMock()
    pet = {"petID": 3, "petName": "Rex"}
    button = KippyActivityCategoriesButton(coordinator, pet)
    await button.async_press()
    coordinator.async_refresh_pet.assert_called_once_with(3)


@pytest.mark.asyncio
async def test_activity_button_propagates_error() -> None:
    """Errors from refresh are raised."""
    coordinator = MagicMock()
    coordinator.async_refresh_pet = AsyncMock(side_effect=RuntimeError)
    pet = {"petID": 3}
    button = KippyActivityCategoriesButton(coordinator, pet)
    with pytest.raises(RuntimeError):
        await button.async_press()
