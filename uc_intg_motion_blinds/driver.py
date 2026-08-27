"""Integration driver for Motion Blinds gateways."""

from ucapi_framework import BaseIntegrationDriver

from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.cover import create_covers
from uc_intg_motion_blinds.device import MotionBlindsDevice
from uc_intg_motion_blinds.sensor import create_sensors


class MotionBlindsDriver(BaseIntegrationDriver[MotionBlindsDevice, MotionBlindsConfig]):
    """Builds a cover entity per blind, plus battery/signal sensors, for each gateway."""

    def __init__(self) -> None:
        super().__init__(
            device_class=MotionBlindsDevice,
            entity_classes=[create_covers, create_sensors],
            driver_id="uc_intg_motion_blinds",
        )
