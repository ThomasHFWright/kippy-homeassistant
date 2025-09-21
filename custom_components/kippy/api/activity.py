"""API endpoint for retrieving activity statistics."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from homeassistant.util import dt as dt_util

from ..const import (
    ACTIVITY_ID,
    FORMULA_GROUP,
    GET_ACTIVITY_CATEGORIES_PATH,
    REQUEST_HEADERS,
    T_ID,
)
from ._base import BaseKippyApi
from ._utils import _tz_hours, _weeks_param


class ActivityEndpoint(BaseKippyApi):
    """Mixin implementing the activity category endpoint."""

    async def get_activity_categories(
        self,
        pet_id: int,
        from_date: str,
        to_date: str,
        time_division: int,
        _weeks: int,
    ) -> Dict[str, Any]:
        """Retrieve activity categories for a pet."""

        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d")

        tzinfo = dt_util.now().tzinfo
        start_ts = int(start.replace(tzinfo=tzinfo).timestamp())
        end_ts = int(end.replace(tzinfo=tzinfo).timestamp())

        tz_hours_value = _tz_hours(start.replace(tzinfo=tzinfo))
        weeks_value = _weeks_param(start, end)

        time_divisions = {1: "h", 2: "d", 3: "w"}.get(time_division, "h")

        payload = await self._authenticated_payload(
            extra={
                "petID": pet_id,
                "activityID": ACTIVITY_ID.ALL,
                "fromDate": start_ts,
                "toDate": end_ts,
                "timeDivisions": time_divisions,
                "formulaGroup": FORMULA_GROUP.SUM,
                "tID": T_ID,
                "timezone": tz_hours_value,
                "weeks": weeks_value,
            }
        )

        data = await self.post_with_refresh(
            GET_ACTIVITY_CATEGORIES_PATH, payload, REQUEST_HEADERS
        )

        if isinstance(data, dict):
            if "data" in data:
                payload = data.get("data") or {}
            else:
                payload = {
                    "activities": data.get("ActivitiesData"),
                    "avg": data.get("AVGData"),
                    "health": data.get("HealthData"),
                }
        else:
            payload = {}

        return {
            "activities": payload.get("activities"),
            "avg": payload.get("avg"),
            "health": payload.get("health"),
        }
