"""Sensor entities - battery level and signal strength per blind."""

import logging
from typing import Any

from ucapi import sensor
from ucapi_framework import SensorEntity

from uc_intg_motion_blinds.config import MotionBlindsConfig
from uc_intg_motion_blinds.const import STATE_UNAVAILABLE
from uc_intg_motion_blinds.device import MotionBlindsDevice

_LOG = logging.getLogger(__name__)


class BatterySensor(SensorEntity):
    """Battery charge (%) of a battery-powered blind."""

    def __init__(self, device_config: MotionBlindsConfig, device: MotionBlindsDevice, meta: dict[str, Any]) -> None:
        self._device = device
        self._mac = meta["mac"]
        safe_mac = self._mac.replace(".", "_")
        super().__init__(
            f"sensor.{device_config.identifier}.{safe_mac}.battery",
            f"{device_config.name} {meta.get('name', 'Blind')} Battery",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: 0},
            device_class=sensor.DeviceClasses.BATTERY,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        value = self._device.battery.get(self._mac)
        if self._device.state == STATE_UNAVAILABLE or value is None:
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: value})


class SignalSensor(SensorEntity):
    """Wi-Fi/RF signal strength (dBm) of a blind."""

    def __init__(self, device_config: MotionBlindsConfig, device: MotionBlindsDevice, meta: dict[str, Any]) -> None:
        self._device = device
        self._mac = meta["mac"]
        safe_mac = self._mac.replace(".", "_")
        super().__init__(
            f"sensor.{device_config.identifier}.{safe_mac}.signal",
            f"{device_config.name} {meta.get('name', 'Blind')} Signal",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: 0},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: "dBm"},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        value = self._device.rssi.get(self._mac)
        if self._device.state == STATE_UNAVAILABLE or value is None:
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: value})


class GatewaySignalSensor(SensorEntity):
    """Wi-Fi signal strength (dBm) of the gateway itself."""

    def __init__(self, device_config: MotionBlindsConfig, device: MotionBlindsDevice) -> None:
        self._device = device
        super().__init__(
            f"sensor.{device_config.identifier}.gateway.signal",
            f"{device_config.name} Gateway Signal",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: 0},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: "dBm"},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        value = self._device.gateway_rssi
        if self._device.state == STATE_UNAVAILABLE or value is None:
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: value})


def create_sensors(device_config: MotionBlindsConfig, device: MotionBlindsDevice) -> list[SensorEntity]:
    """Build a signal sensor per blind, a battery sensor per battery-powered blind, and a gateway signal sensor."""
    entities: list[SensorEntity] = [GatewaySignalSensor(device_config, device)]
    for meta in device_config.blinds:
        if not meta.get("mac"):
            continue
        entities.append(SignalSensor(device_config, device, meta))
        if meta.get("has_battery"):
            entities.append(BatterySensor(device_config, device, meta))
    return entities
