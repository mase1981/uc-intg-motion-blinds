"""Setup flow: enter the gateway API key, auto-discover or enter the gateway IP."""

import asyncio
import logging
import re
from typing import Any

from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow

from uc_intg_motion_blinds import gateway as gw
from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.const import KEY_LENGTH

_LOG = logging.getLogger(__name__)


class MotionBlindsSetupFlow(BaseSetupFlow[MotionBlindsConfig]):
    """Add a Motion Blinds gateway and enumerate its blinds."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._key: str = ""
        self._gateways: list[dict[str, str]] = []

    def get_manual_entry_form(self, error: str = "", values: dict | None = None) -> RequestUserInput:
        values = values or {}
        fields = []
        if error:
            fields.append({
                "id": "error",
                "label": {"en": "Problem"},
                "field": {"label": {"value": {"en": error}}},
            })
        return RequestUserInput(
            {"en": "Motion Blinds Gateway Setup"},
            fields + [
                {
                    "id": "info",
                    "label": {"en": "Motion Blinds Gateway"},
                    "field": {"label": {"value": {"en": (
                        "Open the Motion Blinds / Brel Home / Smart Home app, go to the "
                        "gateway's settings and reveal the 16-character API Key (usually by "
                        "tapping the app version 5 times on the About screen). Enter that key "
                        "below. Leave the IP address blank to discover the gateway "
                        "automatically, or enter it if discovery fails."
                    )}}},
                },
                {
                    "id": "key",
                    "label": {"en": "API Key (16 characters)"},
                    "field": {"text": {"value": values.get("key", "")}},
                },
                {
                    "id": "host",
                    "label": {"en": "Gateway IP Address (optional)"},
                    "field": {"text": {"value": values.get("host", "")}},
                },
            ],
        )

    async def query_device(self, input_values: dict[str, Any]) -> MotionBlindsConfig | RequestUserInput:
        # A gateway picked from the list comes back through here as well.
        if input_values.get("gateway"):
            return await self._from_picker(input_values["gateway"])

        key = re.sub(r"\s+", "", str(input_values.get("key") or ""))
        host = re.sub(r"\s+", "", str(input_values.get("host") or ""))
        values = {"key": key, "host": host}
        if len(key) != KEY_LENGTH:
            return self.get_manual_entry_form(
                f"The API Key must be exactly {KEY_LENGTH} characters (you entered {len(key)}). "
                "Get it from the Motion Blinds app gateway settings.",
                values,
            )
        self._key = key

        if host:
            try:
                return await self._build_config(host, key)
            except ValueError as err:
                return self.get_manual_entry_form(str(err), values)

        _LOG.info("Discovering Motion Blinds gateways on the network...")
        self._gateways = await asyncio.to_thread(gw.discover_gateways, 6.0)
        _LOG.info("Discovered %d gateway(s)", len(self._gateways))

        if not self._gateways:
            return self.get_manual_entry_form(
                "No Motion Blinds gateway was found on the network. Make sure the gateway is "
                "powered on and on the same network as the Remote, then enter its IP address.",
                values,
            )

        if len(self._gateways) == 1:
            try:
                return await self._build_config(self._gateways[0]["host"], key, self._gateways[0].get("mac", ""))
            except ValueError as err:
                return self.get_manual_entry_form(str(err), {**values, "host": self._gateways[0]["host"]})

        items = [
            {"id": g["host"], "label": {"en": f"Gateway {g.get('mac', '')[-4:]} ({g['host']})"}}
            for g in self._gateways
        ]
        return RequestUserInput(
            {"en": "Select Motion Blinds Gateway"},
            [{
                "id": "gateway",
                "label": {"en": "Gateway"},
                "field": {"dropdown": {"value": items[0]["id"], "items": items}},
            }],
        )

    async def handle_additional_configuration_response(self, msg: Any) -> MotionBlindsConfig | RequestUserInput | None:
        # Kept for safety; the picker answer normally arrives in query_device().
        result = await self._from_picker(msg.input_values.get("gateway", ""))
        if isinstance(result, MotionBlindsConfig):
            self._pending_device_config = result
            return None
        self._pending_device_config = None
        return result

    async def _from_picker(self, host: str) -> MotionBlindsConfig | RequestUserInput:
        selected = next((g for g in self._gateways if g["host"] == host), None)
        if not selected:
            return self.get_manual_entry_form("That gateway is no longer listed. Enter its IP address.", {"key": self._key})
        try:
            return await self._build_config(host, self._key, selected.get("mac", ""))
        except ValueError as err:
            return self.get_manual_entry_form(str(err), {"key": self._key, "host": host})

    async def _build_config(self, host: str, key: str, mac: str = "") -> MotionBlindsConfig:
        gateway = gw.build_gateway(host, key)
        try:
            blinds = await asyncio.to_thread(gw.enumerate_blinds, gateway)
        except Exception as err:  # pylint: disable=broad-exception-caught
            raise ValueError(
                f"Could not reach a Motion Blinds gateway at {host}. Check the IP address and "
                f"make sure the gateway is powered on and on the same network. ({err})"
            ) from err

        if not blinds:
            raise ValueError(
                "The gateway was reached but no blinds were found. Make sure blinds are paired "
                "to the gateway in the Motion Blinds app."
            )

        mac = mac or getattr(gateway, "mac", "") or host
        identifier = gw.sanitize_identifier(mac, host)
        name = f"Motion Gateway {mac[-4:].upper()}" if mac else "Motion Gateway"
        return MotionBlindsConfig(
            identifier=identifier,
            name=name,
            host=host,
            key=key,
            mac=mac,
            blinds=blinds,
        )
