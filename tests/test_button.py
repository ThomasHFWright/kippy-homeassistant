from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.kippy.button import (
    KippyActivityCategoriesButton,
    KippyPressButton,
    KippyRefreshPetsButton,
    async_setup_entry,
)
from custom_components.kippy.const import DOMAIN


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


@pytest.mark.asyncio
async def test_button_async_setup_entry_creates_entities() -> None:
    """async_setup_entry adds press and activity buttons for each pet."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    coordinator = MagicMock()
    coordinator.data = {"pets": [{"petID": 1}]}
    map_coord = MagicMock()
    activity_coord = MagicMock()
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "coordinator": coordinator,
                "map_coordinators": {1: map_coord},
                "activity_coordinator": activity_coord,
            }
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert any(isinstance(e, KippyPressButton) for e in entities)
    assert any(isinstance(e, KippyActivityCategoriesButton) for e in entities)
    assert any(isinstance(e, KippyRefreshPetsButton) for e in entities)


@pytest.mark.asyncio
async def test_button_async_setup_entry_no_pets() -> None:
    """No buttons added when there are no pets."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    coordinator = MagicMock()
    coordinator.data = {"pets": []}
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "coordinator": coordinator,
                "map_coordinators": {},
                "activity_coordinator": MagicMock(),
            }
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], KippyRefreshPetsButton)


@pytest.mark.asyncio
async def test_button_async_setup_entry_missing_map() -> None:
    """No buttons added when map coordinator is missing."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    coordinator = MagicMock()
    coordinator.data = {"pets": [{"petID": 1}]}
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "coordinator": coordinator,
                "map_coordinators": {},
                "activity_coordinator": MagicMock(),
            }
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], KippyRefreshPetsButton)


@pytest.mark.asyncio
async def test_refresh_pets_button_reloads_entry() -> None:
    """Refresh pets button reloads the config entry."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    hass.config_entries.async_reload = AsyncMock()
    button = KippyRefreshPetsButton(hass, entry)
    await button.async_press()
    hass.config_entries.async_reload.assert_called_once_with("1")


def test_button_device_info_properties() -> None:
    """Device info includes pet identifiers and name."""
    coordinator = MagicMock()
    pet = {"petID": 7, "kippyID": 9, "petName": "Rex"}
    press = KippyPressButton(coordinator, pet)
    info = press.device_info
    assert info["name"] == "Kippy Rex"
    assert (DOMAIN, "7") in info["identifiers"]

    activity = KippyActivityCategoriesButton(coordinator, pet)
    info2 = activity.device_info
    assert info2["name"] == "Kippy Rex"
