"""Select entities - quick position presets (and favourite) per blind."""

import logging
from typing import Any

from ucapi import StatusCodes, select
from ucapi_framework import SelectEntity

from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.const import (
    POSITION_PRESETS,
    SELECT_FAVORITE,
    SELECT_OPTIONS,
    STATE_UNAVAILABLE,
)
from uc_intg_motion_blinds.device import MotionBlindsDevice

_LOG = logging.getLogger(__name__)


class PositionSelect(SelectEntity):
    """Preset position picker (Open / 75% / 50% / 25% / Closed / Favourite)."""

    def __init__(self, device_config: MotionBlindsConfig, device: MotionBlindsDevice, meta: dict[str, Any]) -> None:
        self._device = device
        self._mac = meta["mac"]
        safe_mac = self._mac.replace(".", "_")
        super().__init__(
            f"select.{device_config.identifier}.{safe_mac}.position",
            f"{device_config.name} {meta.get('name', 'Blind')} Position",
            {
                select.Attributes.STATE: select.States.ON,
                select.Attributes.OPTIONS: SELECT_OPTIONS,
                select.Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    def _current_option(self) -> str:
        position = self._device.cover_position.get(self._mac)
        if position is None:
            return ""
        return min(POSITION_PRESETS, key=lambda label: abs(POSITION_PRESETS[label] - position))

    async def sync_state(self) -> None:
        if self._device.state == STATE_UNAVAILABLE:
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        self.update({
            select.Attributes.STATE: select.States.ON,
            select.Attributes.CURRENT_OPTION: self._current_option(),
        })

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        if cmd_id != select.Commands.SELECT_OPTION:
            return StatusCodes.NOT_IMPLEMENTED
        option = (params or {}).get("option", "")
        if option == SELECT_FAVORITE:
            ok = await self._device.go_favorite(self._mac)
        elif option in POSITION_PRESETS:
            ok = await self._device.set_cover_position(self._mac, POSITION_PRESETS[option])
        else:
            return StatusCodes.BAD_REQUEST
        return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR


def create_selects(device_config: MotionBlindsConfig, device: MotionBlindsDevice) -> list[SelectEntity]:
    """Build a position-preset select for every blind that supports positioning."""
    from uc_intg_motion_blinds.const import TILT_ONLY_TYPES

    selects: list[SelectEntity] = []
    for meta in device_config.blinds:
        if not meta.get("mac"):
            continue
        if meta.get("blind_type", "") in TILT_ONLY_TYPES:
            continue
        selects.append(PositionSelect(device_config, device, meta))
    return selects
