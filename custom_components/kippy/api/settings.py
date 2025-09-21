"""API endpoint for updating tracker settings."""

from __future__ import annotations

from typing import Any, Dict

from ..const import (
    APP_IDENTITY,
    ERROR_NO_AUTH_DATA,
    KIPPYMAP_MODIFY_SETTINGS_PATH,
    REQUEST_HEADERS,
)
from ._base import BaseKippyApi


class SettingsEndpoint(BaseKippyApi):
    """Mixin implementing device settings updates."""

    async def modify_kippy_settings(
        self,
        kippy_id: int,
        *,
        update_frequency: float | None = None,
        gps_on_default: bool | None = None,
        energy_saving_mode: bool | None = None,
    ) -> Dict[str, Any]:
        """Modify settings for a specific device."""

        await self.ensure_login()

        if not self._auth:
            raise RuntimeError(ERROR_NO_AUTH_DATA)

        payload: Dict[str, Any] = {
            "app_code": self.app_code,
            "app_verification_code": self.app_verification_code,
            "app_identity": APP_IDENTITY,
            "modify_kippy_id": kippy_id,
        }
        if update_frequency is not None:
            payload["update_frequency"] = float(f"{float(update_frequency):.1f}")
        if gps_on_default is not None:
            payload["gps_on_default"] = bool(gps_on_default)
        if energy_saving_mode is not None:
            payload["energy_saving_mode"] = int(energy_saving_mode)

        return await self._post_with_refresh(
            KIPPYMAP_MODIFY_SETTINGS_PATH, payload, REQUEST_HEADERS
        )
