import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.kippy.const import (
    LOCALIZATION_TECHNOLOGY_LBS,
    OPERATING_STATUS,
    OPERATING_STATUS_MAP,
)
from custom_components.kippy.coordinator import (
    ActivityRefreshContext,
    ActivityRefreshTimer,
    CoordinatorContext,
    KippyActivityCategoriesDataUpdateCoordinator,
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)


def make_context(hass: MagicMock, api: MagicMock | None = None) -> CoordinatorContext:
    """Return a coordinator context for tests."""

    return CoordinatorContext(hass, MagicMock(), api or MagicMock())


@pytest.mark.asyncio
async def test_process_new_data_maps_operating_status() -> None:
    """process_new_data should map numeric operating status codes."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coordinator = KippyMapDataUpdateCoordinator(make_context(hass), 1)

    coordinator.process_new_data({"operating_status": OPERATING_STATUS.ENERGY_SAVING})

    assert (
        coordinator.data["operating_status"]
        == OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    )


@pytest.mark.asyncio
async def test_data_coordinator_update_success() -> None:
    """_async_update_data returns pets list on success."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    api = MagicMock()
    api.get_pet_kippy_list = AsyncMock(return_value=[{"petID": 1}])
    coordinator = KippyDataUpdateCoordinator(hass, MagicMock(), api)
    data = await coordinator._async_update_data()
    assert data == {"pets": [{"petID": 1}]}


@pytest.mark.asyncio
async def test_data_coordinator_update_failure() -> None:
    """UpdateFailed is raised when API call fails."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    api = MagicMock()
    api.get_pet_kippy_list = AsyncMock(side_effect=RuntimeError)
    coordinator = KippyDataUpdateCoordinator(hass, MagicMock(), api)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_map_coordinator_process_data_ignores_lbs() -> None:
    """LBS data is ignored and previous GPS data reused."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coord = KippyMapDataUpdateCoordinator(make_context(hass), 1)
    coord.ignore_lbs = True
    coord.data = {"gps_latitude": 5, "gps_longitude": 6}
    data = {
        "localization_technology": LOCALIZATION_TECHNOLOGY_LBS,
        "gps_latitude": 1,
        "gps_longitude": 2,
    }
    processed = coord._process_data(data)
    assert processed["gps_latitude"] == 5 and processed["gps_longitude"] == 6


@pytest.mark.asyncio
async def test_map_coordinator_set_refresh_updates_interval() -> None:
    """Setting refresh values updates coordinator interval based on status."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coord = KippyMapDataUpdateCoordinator(make_context(hass), 1)
    coord.data = {"operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]}
    await coord.async_set_live_refresh(20)
    assert coord.update_interval == timedelta(seconds=20)
    coord.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    }
    await coord.async_set_idle_refresh(600)
    assert coord.update_interval == timedelta(seconds=600)


@pytest.mark.asyncio
async def test_map_coordinator_update_failure() -> None:
    """_async_update_data raises UpdateFailed on API error."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    api = MagicMock()
    api.kippymap_action = AsyncMock(side_effect=RuntimeError)
    coord = KippyMapDataUpdateCoordinator(make_context(hass, api), 1)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


@pytest.mark.asyncio
async def test_process_data_without_existing_data_accepts_lbs() -> None:
    """LBS update with no previous data uses provided GPS keys."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coord = KippyMapDataUpdateCoordinator(make_context(hass), 1)
    coord.ignore_lbs = True
    data = {
        "localization_technology": LOCALIZATION_TECHNOLOGY_LBS,
        "gps_latitude": 1,
        "gps_longitude": 2,
    }
    processed = coord._process_data(data)
    assert processed["gps_latitude"] == 1 and processed["gps_longitude"] == 2


@pytest.mark.asyncio
async def test_process_data_without_existing_location_accepts_lbs() -> None:
    """LBS update accepted when existing data lacks GPS coordinates."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coord = KippyMapDataUpdateCoordinator(make_context(hass), 1)
    coord.ignore_lbs = True
    coord.data = {"operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]}
    data = {
        "localization_technology": LOCALIZATION_TECHNOLOGY_LBS,
        "gps_latitude": 3,
        "gps_longitude": 4,
    }
    processed = coord._process_data(data)
    assert processed["gps_latitude"] == 3 and processed["gps_longitude"] == 4


@pytest.mark.asyncio
async def test_process_data_live_sets_interval() -> None:
    """Live status updates refresh interval."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coord = KippyMapDataUpdateCoordinator(make_context(hass), 1)
    coord._process_data({"operating_status": OPERATING_STATUS.LIVE})
    assert coord.update_interval == timedelta(seconds=coord.live_refresh)


@pytest.mark.asyncio
async def test_activity_coordinator_update_and_refresh() -> None:
    """Activity coordinator fetches data and exposes helpers."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    api = MagicMock()
    api.get_activity_categories = AsyncMock(
        return_value={"activities": 1, "avg": 2, "health": 3}
    )
    fake_now = datetime(2020, 1, 2, 12, 0, tzinfo=timezone.utc)

    with patch("homeassistant.util.dt.now", return_value=fake_now):
        coord = KippyActivityCategoriesDataUpdateCoordinator(
            make_context(hass, api), [1]
        )
        assert coord.update_interval is None
        data = await coord._async_update_data()
        api.get_activity_categories.assert_awaited_with(
            1, "2020-01-02", "2020-01-03", 2, 1
        )
        assert data[1]["avg"] == 2
        api.get_activity_categories.side_effect = RuntimeError
        with pytest.raises(UpdateFailed):
            await coord._async_update_data()
        api.get_activity_categories.side_effect = None
        await coord.async_refresh_pet(1)

    assert coord.get_activities(1) == 1
    assert coord.get_avg(1) == 2
    assert coord.get_health(1) == 3


def test_has_config_entry_branches(monkeypatch) -> None:
    """Ensure config_entry kwargs passed when supported."""
    calls = []

    def fake_init(self, hass, logger, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        "custom_components.kippy.coordinator._HAS_CONFIG_ENTRY", True, raising=False
    )
    monkeypatch.setattr(
        "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.__init__",
        fake_init,
    )
    loop = asyncio.new_event_loop()
    hass = MagicMock()
    hass.loop = loop
    api = MagicMock()
    KippyDataUpdateCoordinator(hass, MagicMock(), api)
    KippyMapDataUpdateCoordinator(make_context(hass, api), 1)
    KippyActivityCategoriesDataUpdateCoordinator(make_context(hass, api), [])
    assert all("config_entry" in c for c in calls)


@pytest.mark.asyncio
async def test_activity_refresh_timer_triggers_refreshes() -> None:
    """Timer calls both activity and map coordinators."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    base = MagicMock()
    base.data = {"pets": [{"petID": 1, "updateFrequency": 0}]}
    base.async_add_listener = MagicMock(return_value=lambda: None)
    map_coord = MagicMock()
    map_coord.data = {"contact_time": 0}
    map_coord.async_add_listener = MagicMock(return_value=lambda: None)
    map_coord.async_request_refresh = AsyncMock()
    activity_coord = MagicMock()
    activity_coord.async_refresh_pet = AsyncMock()

    def fake_track(_hass, cb, when):
        hass.loop.call_soon(asyncio.create_task, cb(when))
        return lambda: None

    with patch(
        "custom_components.kippy.coordinator.async_track_point_in_utc_time", fake_track
    ):
        ActivityRefreshTimer(
            ActivityRefreshContext(hass, base, map_coord, activity_coord), 1, 2
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    activity_coord.async_refresh_pet.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_activity_refresh_timer_schedule_controls(monkeypatch) -> None:
    """Timer cancels and reschedules updates safely."""

    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()

    base_unsub_calls = {"count": 0}
    map_unsub_calls = {"count": 0}

    def _base_unsub():
        base_unsub_calls["count"] += 1

    def _map_unsub():
        map_unsub_calls["count"] += 1

    base = MagicMock()
    base.data = {"pets": [{"petID": 1, "updateFrequency": 1}]}
    base.async_add_listener = MagicMock(return_value=_base_unsub)

    map_coord = MagicMock()
    map_coord.data = {"contact_time": 0}
    map_coord.async_add_listener = MagicMock(return_value=_map_unsub)
    map_coord.async_request_refresh = AsyncMock()

    activity = MagicMock()
    activity.async_refresh_pet = AsyncMock()

    scheduled = {"cancellations": 0}

    def fake_track(_hass, _cb, when):
        scheduled["when"] = when

        def _cancel() -> None:
            scheduled["cancellations"] += 1

        return _cancel

    monkeypatch.setattr(
        "custom_components.kippy.coordinator.async_track_point_in_utc_time",
        fake_track,
    )

    timer = ActivityRefreshTimer(
        ActivityRefreshContext(hass, base, map_coord, activity), 1, 2
    )

    base.data = {"pets": []}
    assert timer._get_update_frequency() is None
    base.data = {"pets": [{"petID": 1, "updateFrequency": 1}]}

    timer._schedule_refresh()
    assert scheduled["cancellations"] == 1

    map_coord.data = {"contact_time": "invalid"}
    timer._schedule_refresh()
    assert scheduled["cancellations"] == 2
    assert timer._unsub_timer is None

    map_coord.data = {"contact_time": 0}
    await timer.async_set_delay(5)
    assert timer.delay_minutes == 5

    timer.async_cancel()
    assert scheduled["cancellations"] == 3
    assert base_unsub_calls["count"] == 1
    assert map_unsub_calls["count"] == 1


def test_activity_refresh_timer_clamps_to_future() -> None:
    """Timer clamps past timestamps to now + delay."""
    hass = MagicMock()
    base = MagicMock()
    base.data = {"pets": [{"petID": 1, "updateFrequency": 0}]}
    base.async_add_listener = MagicMock(return_value=lambda: None)
    map_coord = MagicMock()
    map_coord.data = {"contact_time": 0}
    map_coord.async_add_listener = MagicMock(return_value=lambda: None)
    activity_coord = MagicMock()

    scheduled: dict[str, datetime] = {}

    def fake_track(_hass, _cb, when):
        scheduled["when"] = when
        return lambda: None

    now = datetime(2023, 1, 1, tzinfo=timezone.utc)
    with (
        patch("custom_components.kippy.coordinator.dt_util.utcnow", return_value=now),
        patch(
            "custom_components.kippy.coordinator.async_track_point_in_utc_time",
            fake_track,
        ),
    ):
        ActivityRefreshTimer(
            ActivityRefreshContext(hass, base, map_coord, activity_coord), 1, 5
        )

    assert scheduled["when"] == now + timedelta(minutes=5)
