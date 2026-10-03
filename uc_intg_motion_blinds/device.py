"""Motion Blinds gateway device - polls one gateway and all of its blinds.

The gateway speaks a local UDP protocol via the synchronous ``motionblinds``
library, so every socket call is run in a thread and serialized behind a lock
(rule 9). Position/angle are converted to the Unfolded Circle convention here so
the cover entities stay dumb: position 0 = closed, 100 = open.

The first connect often happens while the Remote is still waking up and its
Wi-Fi is not back yet. The framework never retries a connect that raised, so
``establish_connection`` never raises: it retries briefly, then leaves the
device UNAVAILABLE and the poll loop (and any command) connects again later.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from ucapi import cover
from ucapi_framework import DeviceEvents, PollingDevice

from uc_intg_motion_blinds import gateway as gw
from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.const import (
    CLOSED_THRESHOLD_POSITION,
    CLOSED_THRESHOLD_TILT,
    DEFAULT_MAX_ANGLE,
    STATE_ON,
    STATE_UNAVAILABLE,
    TILT_TYPES,
)

_LOG = logging.getLogger(__name__)

_CONNECT_ATTEMPTS = 3  # at start-up, while the Remote's Wi-Fi comes back
_CONNECT_RETRY_DELAY = 5.0
_COMMAND_RECONNECT_GAP = 5.0  # a button press may retry the connection this often


class MotionBlindsDevice(PollingDevice):
    """One Motion Blinds gateway with its attached blinds."""

    def __init__(self, device_config: MotionBlindsConfig, **kwargs: Any) -> None:
        super().__init__(device_config, poll_interval=60, **kwargs)
        self._device_config = device_config
        self._gateway = None
        self._multicast = None
        self._blinds: dict[str, Any] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._state: str = STATE_UNAVAILABLE
        self._connected_once = False
        self._last_attempt = 0.0
        self._failure_logged = False

        self._meta: dict[str, dict[str, Any]] = {
            b["mac"]: b for b in device_config.blinds if b.get("mac")
        }
        self.cover_state: dict[str, str] = {}
        self.cover_position: dict[str, int | None] = {}
        self.cover_tilt: dict[str, int | None] = {}
        self.battery: dict[str, int | None] = {}
        self.rssi: dict[str, int | None] = {}

    # -- identity ------------------------------------------------------
    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    @property
    def state(self) -> str:
        return self._state

    @property
    def gateway_rssi(self) -> int | None:
        rssi = getattr(self._gateway, "RSSI", None)
        return int(rssi) if rssi is not None else None

    @property
    def gateway_firmware(self) -> str | None:
        return getattr(self._gateway, "firmware", None)

    def blind_meta(self, mac: str) -> dict[str, Any]:
        return self._meta.get(mac, {})

    # -- connection lifecycle ------------------------------------------
    async def establish_connection(self):
        """Connect to the gateway; never raises (see module docstring)."""
        for attempt in range(1, _CONNECT_ATTEMPTS + 1):
            if await self._try_connect():
                break
            if attempt < _CONNECT_ATTEMPTS:
                await asyncio.sleep(_CONNECT_RETRY_DELAY)
        self.push_update()
        return self._gateway

    async def _try_connect(self) -> bool:
        """Build the gateway objects and read the blind list. Returns success."""
        async with self._lock:
            self._last_attempt = time.monotonic()
            try:
                await self._rebuild_gateway()
                await asyncio.to_thread(self._gateway.GetDeviceList)
                await asyncio.to_thread(self._gateway.Update)
            except Exception as err:  # pylint: disable=broad-exception-caught
                log = _LOG.debug if self._failure_logged else _LOG.warning
                log("[%s] Cannot reach gateway at %s: %s (will retry)", self.log_id, self.address, err)
                self._failure_logged = True
                self._state = STATE_UNAVAILABLE
                return False

            self._blinds = dict(self._gateway.device_list)
            for mac, blind in self._blinds.items():
                blind.Register_callback(self.identifier, self._on_gateway_push)
                try:
                    await asyncio.to_thread(blind.Update_from_cache)
                except Exception as err:  # pylint: disable=broad-exception-caught
                    _LOG.debug("[%s] Initial read failed for %s: %s", self.log_id, mac, err)
            self._refresh_cache()
            self._state = STATE_ON
            self._failure_logged = False
            if self._connected_once:
                _LOG.info("[%s] Gateway reachable again", self.log_id)
            self._connected_once = True
        return True

    async def _rebuild_gateway(self) -> None:
        """Fresh gateway and multicast listener (a listener made while offline stays deaf)."""
        await self._stop_multicast()
        multicast = gw.build_multicast()
        try:
            await asyncio.to_thread(multicast.Start_listen)
            self._multicast = multicast
        except Exception as err:  # pylint: disable=broad-exception-caught
            # Push updates are optional; polling still keeps the state current.
            _LOG.debug("[%s] Multicast listener not started: %s", self.log_id, err)
            multicast = None
        self._gateway = gw.build_gateway(self._device_config.host, self._device_config.key, multicast)
        self._gateway.Register_callback(self.identifier, self._on_gateway_push)

    async def _stop_multicast(self) -> None:
        if self._multicast is None:
            return
        multicast, self._multicast = self._multicast, None
        try:
            multicast.Unregister_motion_gateway(self._device_config.host)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        try:
            await asyncio.to_thread(multicast.Stop_listen)
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.debug("[%s] Multicast stop failed: %s", self.log_id, err)

    async def poll_device(self) -> None:
        if not self._blinds:
            # Never connected (or lost the blind list): try again every poll.
            if await self._try_connect():
                self.events.emit(DeviceEvents.CONNECTED, self.identifier)
            self.push_update()
            return
        try:
            async with self._lock:
                await asyncio.to_thread(self._gateway.Update)
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.debug("[%s] Poll error: %s", self.log_id, err)
            if self._state != STATE_UNAVAILABLE:
                self._state = STATE_UNAVAILABLE
                self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)
            return

        for mac, blind in list(self._blinds.items()):
            try:
                async with self._lock:
                    await asyncio.to_thread(blind.Update_from_cache)
            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOG.debug("[%s] Poll read failed for %s: %s", self.log_id, mac, err)

        self._refresh_cache()
        if self._state != STATE_ON:
            self._state = STATE_ON
            _LOG.info("[%s] Gateway reachable again", self.log_id)
            self.events.emit(DeviceEvents.CONNECTED, self.identifier)
        self.push_update()

    def _on_gateway_push(self) -> None:
        """Marshal a multicast push from the listener thread onto the event loop."""
        self._loop.call_soon_threadsafe(self._handle_gateway_push)

    def _handle_gateway_push(self) -> None:
        self._refresh_cache()
        if self._state != STATE_ON:
            self._state = STATE_ON
        self.push_update()

    async def disconnect(self) -> None:
        async with self._lock:
            await self._stop_multicast()
            self._gateway = None
            self._blinds = {}
        self._state = STATE_UNAVAILABLE
        await super().disconnect()

    # -- state conversion ----------------------------------------------
    def _refresh_cache(self) -> None:
        for mac, blind in self._blinds.items():
            meta = self._meta.get(mac, {})
            has_tilt = meta.get("blind_type", "") in TILT_TYPES
            raw_pos = getattr(blind, "position", None)
            raw_angle = getattr(blind, "angle", None)
            status = getattr(blind, "status", None)
            status_name = status if isinstance(status, str) else ""

            if raw_pos is None:
                self.cover_position[mac] = None
            else:
                self.cover_position[mac] = max(0, min(100, 100 - int(raw_pos)))

            if has_tilt and raw_angle is not None:
                max_angle = meta.get("max_angle", DEFAULT_MAX_ANGLE) or DEFAULT_MAX_ANGLE
                self.cover_tilt[mac] = max(0, min(100, round(100 - (int(raw_angle) * 100 / max_angle))))
            else:
                self.cover_tilt[mac] = None

            self.cover_state[mac] = self._derive_state(status_name, raw_pos, has_tilt)

            battery = getattr(blind, "battery_level", None)
            self.battery[mac] = int(battery) if battery is not None else None
            rssi = getattr(blind, "RSSI", None)
            self.rssi[mac] = int(rssi) if rssi is not None else None

    @staticmethod
    def _derive_state(status_name: str, raw_pos: int | None, has_tilt: bool) -> str:
        if status_name == "Opening":
            return cover.States.OPENING
        if status_name == "Closing":
            return cover.States.CLOSING
        if raw_pos is None:
            return cover.States.UNKNOWN
        threshold = CLOSED_THRESHOLD_TILT if has_tilt else CLOSED_THRESHOLD_POSITION
        return cover.States.CLOSED if raw_pos >= threshold else cover.States.OPEN

    # -- commands ------------------------------------------------------
    async def _run_blind(self, mac: str, method: str, *args: Any) -> bool:
        blind = self._blinds.get(mac)
        if blind is None and not self._blinds:
            # Not connected yet (e.g. the Remote just woke up): connect now, then run it.
            if time.monotonic() - self._last_attempt >= _COMMAND_RECONNECT_GAP and await self._try_connect():
                self.push_update()
                blind = self._blinds.get(mac)
        if blind is None:
            _LOG.warning("[%s] Unknown blind: %s", self.log_id, mac)
            return False
        fn = getattr(blind, method, None)
        if fn is None:
            _LOG.warning("[%s] Blind %s has no method %s", self.log_id, mac, method)
            return False
        try:
            async with self._lock:
                await asyncio.to_thread(fn, *args)
            return True
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.warning("[%s] %s(%s) failed on %s: %s", self.log_id, method, args, mac, err)
            return False

    async def open_cover(self, mac: str) -> bool:
        return await self._run_blind(mac, "Open")

    async def close_cover(self, mac: str) -> bool:
        return await self._run_blind(mac, "Close")

    async def stop_cover(self, mac: str) -> bool:
        return await self._run_blind(mac, "Stop")

    async def set_cover_position(self, mac: str, uc_position: int) -> bool:
        uc_position = max(0, min(100, int(uc_position)))
        return await self._run_blind(mac, "Set_position", 100 - uc_position)

    async def set_cover_tilt(self, mac: str, uc_tilt: int) -> bool:
        uc_tilt = max(0, min(100, int(uc_tilt)))
        max_angle = self._meta.get(mac, {}).get("max_angle", DEFAULT_MAX_ANGLE) or DEFAULT_MAX_ANGLE
        angle = round((100 - uc_tilt) * max_angle / 100)
        return await self._run_blind(mac, "Set_angle", angle)

    async def tilt_up(self, mac: str) -> bool:
        return await self._run_blind(mac, "Jog_up")

    async def tilt_down(self, mac: str) -> bool:
        return await self._run_blind(mac, "Jog_down")

    async def tilt_stop(self, mac: str) -> bool:
        return await self._run_blind(mac, "Stop")

    async def go_favorite(self, mac: str) -> bool:
        return await self._run_blind(mac, "Go_favorite_position")
