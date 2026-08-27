"""Cover entities - one per blind attached to a Motion Blinds gateway."""

import logging
from typing import Any

from ucapi import StatusCodes, cover
from ucapi_framework import CoverEntity

from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.const import STATE_UNAVAILABLE, TILT_ONLY_TYPES, TILT_TYPES
from uc_intg_motion_blinds.device import MotionBlindsDevice

_LOG = logging.getLogger(__name__)


class MotionBlindCover(CoverEntity):
    """A single blind exposed as a cover."""

    def __init__(self, device_config: MotionBlindsConfig, device: MotionBlindsDevice, meta: dict[str, Any]) -> None:
        self._device = device
        self._mac = meta["mac"]
        blind_type = meta.get("blind_type", "")
        self._has_tilt = blind_type in TILT_TYPES
        self._tilt_only = blind_type in TILT_ONLY_TYPES

        features = [cover.Features.OPEN, cover.Features.CLOSE, cover.Features.STOP]
        attributes: dict[str, Any] = {cover.Attributes.STATE: cover.States.UNKNOWN}
        if not self._tilt_only:
            features.append(cover.Features.POSITION)
            attributes[cover.Attributes.POSITION] = 0
        if self._has_tilt:
            features += [cover.Features.TILT, cover.Features.TILT_STOP, cover.Features.TILT_POSITION]
            attributes[cover.Attributes.TILT_POSITION] = 0

        safe_mac = self._mac.replace(".", "_")
        entity_id = f"cover.{device_config.identifier}.{safe_mac}"
        name = meta.get("name") or f"{device_config.name} Blind"
        super().__init__(
            entity_id,
            f"{device_config.name} {name}".strip(),
            features,
            attributes,
            device_class=cover.DeviceClasses.BLIND,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == STATE_UNAVAILABLE:
            self.update({cover.Attributes.STATE: cover.States.UNAVAILABLE})
            return

        attrs: dict[str, Any] = {
            cover.Attributes.STATE: self._device.cover_state.get(self._mac, cover.States.UNKNOWN)
        }
        if not self._tilt_only:
            position = self._device.cover_position.get(self._mac)
            if position is not None:
                attrs[cover.Attributes.POSITION] = position
        if self._has_tilt:
            tilt = self._device.cover_tilt.get(self._mac)
            if tilt is not None:
                attrs[cover.Attributes.TILT_POSITION] = tilt
        self.update(attrs)

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        params = params or {}
        ok = False
        if cmd_id == cover.Commands.OPEN:
            self.update({cover.Attributes.STATE: cover.States.OPENING})
            ok = await self._device.open_cover(self._mac)
        elif cmd_id == cover.Commands.CLOSE:
            self.update({cover.Attributes.STATE: cover.States.CLOSING})
            ok = await self._device.close_cover(self._mac)
        elif cmd_id == cover.Commands.STOP:
            ok = await self._device.stop_cover(self._mac)
        elif cmd_id == cover.Commands.POSITION:
            target = int(params.get("position", 0))
            current = self._device.cover_position.get(self._mac)
            if current is not None:
                self.update({
                    cover.Attributes.STATE: cover.States.OPENING
                    if target > current
                    else cover.States.CLOSING
                })
            ok = await self._device.set_cover_position(self._mac, target)
        elif cmd_id == cover.Commands.TILT:
            target = int(params.get("tilt_position", params.get("position", 0)))
            ok = await self._device.set_cover_tilt(self._mac, target)
        elif cmd_id == cover.Commands.TILT_UP:
            ok = await self._device.tilt_up(self._mac)
        elif cmd_id == cover.Commands.TILT_DOWN:
            ok = await self._device.tilt_down(self._mac)
        elif cmd_id == cover.Commands.TILT_STOP:
            ok = await self._device.tilt_stop(self._mac)
        else:
            return StatusCodes.NOT_IMPLEMENTED
        return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR


def create_covers(device_config: MotionBlindsConfig, device: MotionBlindsDevice) -> list[CoverEntity]:
    """Build one cover entity per blind persisted in the gateway config."""
    covers: list[CoverEntity] = []
    for meta in device_config.blinds:
        if meta.get("mac"):
            covers.append(MotionBlindCover(device_config, device, meta))
    return covers
