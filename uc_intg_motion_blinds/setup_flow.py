"""Setup flow: enter the gateway API key, auto-discover or enter the gateway IP."""

import asyncio
import logging
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

    def get_manual_entry_form(self) -> RequestUserInput:
        return RequestUserInput(
            {"en": "Motion Blinds Gateway Setup"},
            [
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
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "host",
                    "label": {"en": "Gateway IP Address (optional)"},
                    "field": {"text": {"value": ""}},
                },
            ],
        )

    async def query_device(self, input_values: dict[str, Any]) -> MotionBlindsConfig | RequestUserInput:
        key = input_values.get("key", "").strip()
        if len(key) != KEY_LENGTH:
            raise ValueError(
                f"The API Key must be exactly {KEY_LENGTH} characters. Get it from the Motion "
                "Blinds app gateway settings."
            )
        self._key = key
        host = input_values.get("host", "").strip()

        if host:
            return await self._build_config(host, key)

        _LOG.info("Discovering Motion Blinds gateways on the network...")
        self._gateways = await asyncio.to_thread(gw.discover_gateways, 6.0)
        _LOG.info("Discovered %d gateway(s)", len(self._gateways))

        if not self._gateways:
            raise ValueError(
                "No Motion Blinds gateway was found on the network. Make sure the gateway is "
                "powered on and on the same network as the Remote, then try again and enter "
                "the IP address manually."
            )

        if len(self._gateways) == 1:
            return await self._build_config(self._gateways[0]["host"], key, self._gateways[0].get("mac", ""))

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

    async def handle_additional_configuration_response(self, msg: Any) -> MotionBlindsConfig | None:
        host = msg.input_values.get("gateway", "")
        selected = next((g for g in self._gateways if g["host"] == host), None)
        if not selected:
            raise ValueError("Selected gateway not found")
        self._pending_device_config = await self._build_config(host, self._key, selected.get("mac", ""))
        return None

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
