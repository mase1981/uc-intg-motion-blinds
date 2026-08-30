"""Integration driver for Motion Blinds gateways."""

from ucapi_framework import BaseIntegrationDriver

from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.cover import create_covers
from uc_intg_motion_blinds.device import MotionBlindsDevice
from uc_intg_motion_blinds.remote import create_remote
from uc_intg_motion_blinds.select import create_selects
from uc_intg_motion_blinds.sensor import create_sensors


class MotionBlindsDriver(BaseIntegrationDriver[MotionBlindsDevice, MotionBlindsConfig]):
    """Builds a cover, position select and sensors per blind, plus a gateway-wide remote."""

    def __init__(self) -> None:
        super().__init__(
            device_class=MotionBlindsDevice,
            entity_classes=[create_covers, create_selects, create_sensors, create_remote],
            driver_id="uc_intg_motion_blinds",
        )
