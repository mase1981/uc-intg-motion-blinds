"""Thin helpers around the synchronous ``motionblinds`` library.

The ``motionblinds`` library is blocking (UDP sockets), so every call here is
meant to be run inside ``asyncio.to_thread`` by the caller. The device and the
setup flow both build gateways through these helpers.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from motionblinds import MotionDiscovery, MotionGateway

from uc_intg_motion_blinds.const import DEFAULT_MAX_ANGLE

_LOG = logging.getLogger(__name__)


def build_gateway(host: str, key: str) -> MotionGateway:
    """Create a MotionGateway bound to a host and API key."""
    return MotionGateway(ip=host, key=key)


def discover_gateways(timeout: float = 6.0) -> list[dict[str, str]]:
    """Broadcast for gateways on the LAN and return ``[{host, mac}]``."""
    found = MotionDiscovery(discovery_time=timeout).discover()
    gateways: list[dict[str, str]] = []
    for host, info in (found or {}).items():
        mac = ""
        if isinstance(info, dict):
            mac = info.get("mac", "") or info.get("token", "")
        gateways.append({"host": host, "mac": mac})
    return gateways


def _blind_type_name(blind: Any) -> str:
    blind_type = getattr(blind, "blind_type", None)
    if blind_type is None:
        return ""
    return getattr(blind_type, "name", str(blind_type))


def enumerate_blinds(gateway: MotionGateway) -> list[dict[str, Any]]:
    """Populate the gateway device list and return persisted blind metadata."""
    gateway.GetDeviceList()
    blinds: list[dict[str, Any]] = []
    for mac, blind in gateway.device_list.items():
        try:
            blind.Update()
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.debug("Initial update failed for blind %s: %s", mac, err)
        max_angle = getattr(blind, "max_angle", DEFAULT_MAX_ANGLE) or DEFAULT_MAX_ANGLE
        blind_type = _blind_type_name(blind)
        blinds.append(
            {
                "mac": mac,
                "name": _friendly_name(blind_type, mac),
                "blind_type": blind_type,
                "device_type": getattr(blind, "device_type", "") or "",
                "max_angle": int(max_angle),
            }
        )
    return blinds


def _friendly_name(blind_type: str, mac: str) -> str:
    label = re.sub(r"(?<!^)(?=[A-Z])", " ", blind_type).strip() if blind_type else "Blind"
    suffix = mac[-4:].upper() if mac else ""
    return f"{label} {suffix}".strip()


def sanitize_identifier(mac: str, host: str) -> str:
    """Build a stable, dot-free device identifier from the gateway mac/host."""
    base = mac or host
    return f"motion_{re.sub(r'[^A-Za-z0-9]', '_', base)}"
