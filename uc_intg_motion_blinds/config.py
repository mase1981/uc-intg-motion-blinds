"""Configuration dataclass and manager for the Motion Blinds integration."""

from dataclasses import dataclass, field
from typing import Any

from ucapi_framework import BaseConfigManager


@dataclass
class MotionBlindsConfig:
    """Configuration for a single Motion Blinds gateway and its blinds.

    ``blinds`` is a list of dicts persisted at setup so entities can be built
    without a live connection (each: ``mac``, ``name``, ``blind_type``,
    ``device_type``, ``max_angle``).
    """

    identifier: str = ""
    name: str = ""
    host: str = ""
    key: str = ""
    mac: str = ""
    blinds: list[dict[str, Any]] = field(default_factory=list)


class MotionBlindsConfigManager(BaseConfigManager[MotionBlindsConfig]):
    """Config manager bound to :class:`MotionBlindsConfig`."""
