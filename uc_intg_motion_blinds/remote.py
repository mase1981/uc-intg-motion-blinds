"""Remote entity - one dashboard per gateway with a UI page per blind."""

import asyncio
import logging
import re
from typing import Any

from ucapi import StatusCodes, remote
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_text
from ucapi_framework import RemoteEntity

from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.const import (
    ALL_CLOSE,
    ALL_OPEN,
    ALL_STOP,
    STATE_UNAVAILABLE,
    TILT_ONLY_TYPES,
    TILT_TYPES,
)
from uc_intg_motion_blinds.device import MotionBlindsDevice

_LOG = logging.getLogger(__name__)

_GRID = Size(4, 6)


class MotionBlindsRemote(RemoteEntity):
    """Gateway-wide remote: overview page plus one control page per blind."""

    def __init__(self, device_config: MotionBlindsConfig, device: MotionBlindsDevice) -> None:
        self._device = device
        self._blinds = [b for b in device_config.blinds if b.get("mac")]
        self._cmd_map: dict[str, tuple[str, str]] = {}
        self._build_command_map()

        commands = [ALL_OPEN, ALL_CLOSE, ALL_STOP, *self._cmd_map.keys()]
        button_mapping = [
            create_btn_mapping(Buttons.DPAD_UP, ALL_OPEN),
            create_btn_mapping(Buttons.DPAD_DOWN, ALL_CLOSE),
            create_btn_mapping(Buttons.DPAD_MIDDLE, ALL_STOP),
            create_btn_mapping(Buttons.STOP, ALL_STOP),
        ]

        super().__init__(
            f"remote.{device_config.identifier}",
            f"{device_config.name} Remote",
            [remote.Features.ON_OFF, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.ON},
            simple_commands=commands,
            button_mapping=button_mapping,
            ui_pages=self._build_ui_pages(),
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    def _build_command_map(self) -> None:
        used: set[str] = set()
        for index, meta in enumerate(self._blinds):
            slug = re.sub(r"_+", "_", re.sub(r"[^A-Z0-9]", "_", meta.get("name", "").upper())).strip("_")
            slug = slug or f"BLIND_{index + 1}"
            while slug in used:
                slug = f"{slug}_{index + 1}"
            used.add(slug)
            meta["_slug"] = slug
            mac = meta["mac"]
            blind_type = meta.get("blind_type", "")

            self._cmd_map[f"{slug}_OPEN"] = (mac, "OPEN")
            self._cmd_map[f"{slug}_CLOSE"] = (mac, "CLOSE")
            self._cmd_map[f"{slug}_STOP"] = (mac, "STOP")
            self._cmd_map[f"{slug}_FAV"] = (mac, "FAV")
            if blind_type in TILT_TYPES:
                self._cmd_map[f"{slug}_TILT_UP"] = (mac, "TILT_UP")
                self._cmd_map[f"{slug}_TILT_DOWN"] = (mac, "TILT_DOWN")
            if blind_type not in TILT_ONLY_TYPES:
                for pct in (25, 50, 75):
                    self._cmd_map[f"{slug}_POS_{pct}"] = (mac, f"POS_{pct}")

    def _build_ui_pages(self) -> list[UiPage]:
        overview = UiPage(page_id="overview", name="All Blinds", grid=_GRID)
        overview.add(create_ui_text(self._device.name, 0, 0, Size(4, 1)))
        overview.add(create_ui_text("Open All", 0, 1, Size(2, 1), ALL_OPEN))
        overview.add(create_ui_text("Close All", 2, 1, Size(2, 1), ALL_CLOSE))
        overview.add(create_ui_text("Stop All", 0, 2, Size(4, 1), ALL_STOP))
        pages: list[UiPage] = [overview]

        for meta in self._blinds:
            pages.append(self._build_blind_page(meta))
        return pages

    def _build_blind_page(self, meta: dict[str, Any]) -> UiPage:
        slug = meta["_slug"]
        blind_type = meta.get("blind_type", "")
        page = UiPage(page_id=f"blind_{slug}", name=meta.get("name", "Blind"), grid=_GRID)
        page.add(create_ui_text(meta.get("name", "Blind"), 0, 0, Size(4, 1)))
        page.add(create_ui_text("Open", 0, 1, Size(2, 1), f"{slug}_OPEN"))
        page.add(create_ui_text("Close", 2, 1, Size(2, 1), f"{slug}_CLOSE"))
        page.add(create_ui_text("Stop", 0, 2, Size(2, 1), f"{slug}_STOP"))
        page.add(create_ui_text("Favourite", 2, 2, Size(2, 1), f"{slug}_FAV"))

        if blind_type not in TILT_ONLY_TYPES:
            page.add(create_ui_text("25%", 0, 3, Size(1, 1), f"{slug}_POS_25"))
            page.add(create_ui_text("50%", 1, 3, Size(1, 1), f"{slug}_POS_50"))
            page.add(create_ui_text("75%", 2, 3, Size(1, 1), f"{slug}_POS_75"))
        if blind_type in TILT_TYPES:
            page.add(create_ui_text("Tilt +", 0, 4, Size(2, 1), f"{slug}_TILT_UP"))
            page.add(create_ui_text("Tilt -", 2, 4, Size(2, 1), f"{slug}_TILT_DOWN"))
        return page

    async def sync_state(self) -> None:
        state = remote.States.UNAVAILABLE if self._device.state == STATE_UNAVAILABLE else remote.States.ON
        self.update({remote.Attributes.STATE: state})

    async def _run_action(self, mac: str, action: str) -> bool:
        if action == "OPEN":
            return await self._device.open_cover(mac)
        if action == "CLOSE":
            return await self._device.close_cover(mac)
        if action == "STOP":
            return await self._device.stop_cover(mac)
        if action == "FAV":
            return await self._device.go_favorite(mac)
        if action == "TILT_UP":
            return await self._device.tilt_up(mac)
        if action == "TILT_DOWN":
            return await self._device.tilt_down(mac)
        if action.startswith("POS_"):
            return await self._device.set_cover_position(mac, int(action[4:]))
        return False

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        params = params or {}
        if cmd_id == remote.Commands.ON:
            self.update({remote.Attributes.STATE: remote.States.ON})
            return StatusCodes.OK
        if cmd_id == remote.Commands.OFF:
            self.update({remote.Attributes.STATE: remote.States.OFF})
            return StatusCodes.OK
        if cmd_id not in (remote.Commands.SEND_CMD, remote.Commands.SEND_CMD_SEQUENCE):
            return StatusCodes.NOT_IMPLEMENTED

        if cmd_id == remote.Commands.SEND_CMD_SEQUENCE:
            commands = params.get("sequence") or []
            if isinstance(commands, str):
                commands = commands.split(",")
        else:
            commands = [params.get("command", "")]
        commands = [str(command).strip() for command in commands if str(command).strip()]
        if not commands:
            return StatusCodes.BAD_REQUEST

        repeat, delay = _repeat_delay(params)
        ok = True
        first = True
        for _ in range(repeat):
            for command in commands:
                if not first and delay:
                    await asyncio.sleep(delay)
                first = False
                ok = await self._dispatch(command) and ok
        return StatusCodes.OK if ok else StatusCodes.SERVER_ERROR

    async def _dispatch(self, command: str) -> bool:
        if command in (ALL_OPEN, ALL_CLOSE, ALL_STOP):
            action = {ALL_OPEN: "OPEN", ALL_CLOSE: "CLOSE", ALL_STOP: "STOP"}[command]
            results = [await self._run_action(b["mac"], action) for b in self._blinds]
            return any(results)
        target = self._cmd_map.get(command) or self._cmd_map.get(command.upper())
        if target is None:
            _LOG.warning("Unknown remote command: %s", command)
            return False
        return await self._run_action(*target)


def _repeat_delay(params: dict[str, Any]) -> tuple[int, float]:
    """Repeat count (at least 1) and delay in seconds from the command parameters."""
    try:
        repeat = max(1, int(params.get("repeat") or 1))
    except (TypeError, ValueError):
        repeat = 1
    try:
        delay = max(0, int(params.get("delay") or 0)) / 1000
    except (TypeError, ValueError):
        delay = 0.0
    return repeat, delay


def create_remote(device_config: MotionBlindsConfig, device: MotionBlindsDevice) -> list[RemoteEntity]:
    """Build one gateway-wide remote if the gateway has any blinds."""
    if not any(b.get("mac") for b in device_config.blinds):
        return []
    return [MotionBlindsRemote(device_config, device)]
