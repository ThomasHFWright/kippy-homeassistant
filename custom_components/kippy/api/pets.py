"""API endpoint dealing with pet metadata."""

from __future__ import annotations

from typing import Any

from ..const import (
    APP_SUB_IDENTITY,
    GET_PETS_PATH,
    REQUEST_HEADERS,
)
from ._base import BaseKippyApi


class PetsEndpoint(BaseKippyApi):
    """Mixin providing access to the pet list endpoint."""

    async def get_pet_kippy_list(self) -> list[dict[str, Any]]:
        """Retrieve the list of pets associated with the account."""

        payload = await self._authenticated_payload(
            extra={"app_sub_identity": APP_SUB_IDENTITY}
        )

        data = await self.post_with_refresh(GET_PETS_PATH, payload, REQUEST_HEADERS)
        pets = data.get("data", [])
        for pet in pets:
            if not isinstance(pet, dict):
                continue
            if "enableGPSOnDefault" in pet and "gpsOnDefault" not in pet:
                value = pet.pop("enableGPSOnDefault")
                if isinstance(value, str):
                    try:
                        value = int(value)
                    except ValueError:
                        value = 1 if value.lower() in ("true", "1") else 0
                pet["gpsOnDefault"] = int(bool(value))
        return pets
