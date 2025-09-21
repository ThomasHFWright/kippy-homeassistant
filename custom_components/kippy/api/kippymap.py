"""API endpoint for fetching Kippy Map location data."""

from __future__ import annotations

from typing import Any, Dict

from ..const import (
    KIPPYMAP_ACTION_PATH,
    LOCALIZATION_TECHNOLOGY_MAP,
    REQUEST_HEADERS,
)
from ._base import BaseKippyApi


class KippyMapEndpoint(BaseKippyApi):
    """Mixin implementing the Kippy Map action endpoint."""

    async def kippymap_action(
        self,
        kippy_id: int,
        do_sms: bool = True,
        app_action: int | None = None,
        geofence_id: int | None = None,
    ) -> Dict[str, Any]:
        """Perform a Kippy Map action for a specific device."""

        payload = await self._authenticated_payload(
            extra={
                "kippy_id": kippy_id,
                "do_sms": int(do_sms),
            }
        )
        if app_action is not None:
            payload["app_action"] = app_action
        if geofence_id is not None:
            payload["geofence_id"] = geofence_id

        data = await self.post_with_refresh(
            KIPPYMAP_ACTION_PATH, payload, REQUEST_HEADERS
        )

        response = data.get("data")
        if not isinstance(response, dict):
            response = dict(data)

        lat = response.pop("lat", None)
        if lat is not None:
            response["gps_latitude"] = lat
        lng = response.pop("lng", None)
        if lng is not None:
            response["gps_longitude"] = lng
        radius = response.pop("radius", None)
        if radius is not None:
            response["gps_accuracy"] = radius
        altitude = response.pop("altitude", None)
        if altitude is not None:
            response["gps_altitude"] = altitude

        tech = response.get("localization_tecnology")
        if tech is not None:
            response["localization_technology"] = LOCALIZATION_TECHNOLOGY_MAP.get(
                str(tech), str(tech)
            )

        return response
