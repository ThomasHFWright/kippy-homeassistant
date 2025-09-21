import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError

from custom_components.kippy.button import (
    KippyActivityCategoriesButton,
    KippyRefreshMapAttributesButton,
    KippyRefreshPetsButton,
    async_setup_entry,
)
from custom_components.kippy.const import DOMAIN


@pytest.mark.asyncio
async def test_refresh_map_attributes_button_calls_api_and_processes_data() -> None:
    """Refresh Map Attributes button triggers API call and processes returned data."""
    coordinator = MagicMock()
    coordinator.api.kippymap_action = AsyncMock(return_value={"ok": True})
    coordinator.process_new_data = MagicMock()
    coordinator.kippy_id = 5
    pet = {"petID": 5, "petName": "Rex"}
    button = KippyRefreshMapAttributesButton(coordinator, pet)
    await button.async_press()
    coordinator.api.kippymap_action.assert_called_once_with(5)
    coordinator.process_new_data.assert_called_once_with({"ok": True})


@pytest.mark.asyncio
async def test_refresh_map_attributes_button_propagates_error() -> None:
    """Exceptions from API are not swallowed."""
    coordinator = MagicMock()
    coordinator.api.kippymap_action = AsyncMock(side_effect=RuntimeError)
    coordinator.process_new_data = MagicMock()
    coordinator.kippy_id = 5
    pet = {"petID": 5}
    button = KippyRefreshMapAttributesButton(coordinator, pet)
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
    """async_setup_entry adds refresh and activity buttons for each pet."""
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
    refresh_map_button_present = False
    activity_button_present = False
    refresh_pets_button_present = False
    for entity in entities:
        if isinstance(entity, KippyRefreshMapAttributesButton):
            refresh_map_button_present = True
        if isinstance(entity, KippyActivityCategoriesButton):
            activity_button_present = True
        if isinstance(entity, KippyRefreshPetsButton):
            refresh_pets_button_present = True

    assert refresh_map_button_present
    assert activity_button_present
    assert refresh_pets_button_present


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
    entry.state = ConfigEntryState.LOADED
    hass.config_entries.async_reload = AsyncMock()
    hass.async_create_task = MagicMock(
        side_effect=lambda coro: asyncio.create_task(coro)
    )
    button = KippyRefreshPetsButton(hass, entry)
    await button.async_press()
    hass.config_entries.async_reload.assert_called_once_with("1")
    hass.async_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_pets_button_not_pressable_when_entry_not_loaded() -> None:
    """Refresh pets button raises when entry is not loaded."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    entry.state = ConfigEntryState.NOT_LOADED
    hass.config_entries.async_reload = AsyncMock()
    button = KippyRefreshPetsButton(hass, entry)
    with pytest.raises(HomeAssistantError):
        await button.async_press()
    hass.config_entries.async_reload.assert_not_called()


def test_button_device_info_properties() -> None:
    """Device info includes pet identifiers and name."""
    coordinator = MagicMock()
    pet = {"petID": 7, "kippyID": 9, "petName": "Rex"}
    refresh = KippyRefreshMapAttributesButton(coordinator, pet)
    info = refresh.device_info
    assert info["name"] == "Kippy Rex"
    assert (DOMAIN, "7") in info["identifiers"]

    activity = KippyActivityCategoriesButton(coordinator, pet)
    info2 = activity.device_info
    assert info2["name"] == "Kippy Rex"


def test_buttons_raise_for_sync_press() -> None:
    """Synchronous press methods are intentionally unsupported."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    map_button = KippyRefreshMapAttributesButton(coordinator, {"petID": 1})
    with pytest.raises(NotImplementedError):
        map_button.press()

    activity_button = KippyActivityCategoriesButton(MagicMock(), {"petID": 2})
    with pytest.raises(NotImplementedError):
        activity_button.press()

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    pets_button = KippyRefreshPetsButton(hass, entry)
    with pytest.raises(NotImplementedError):
        pets_button.press()
