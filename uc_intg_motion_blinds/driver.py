"""Integration driver for Motion Blinds gateways."""

from ucapi_framework import BaseIntegrationDriver

from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.cover import create_covers
from uc_intg_motion_blinds.device import MotionBlindsDevice


class MotionBlindsDriver(BaseIntegrationDriver[MotionBlindsDevice, MotionBlindsConfig]):
    """Builds a cover entity per blind attached to each gateway."""

    def __init__(self) -> None:
        super().__init__(
            device_class=MotionBlindsDevice,
            entity_classes=[create_covers],
            driver_id="uc_intg_motion_blinds",
        )
