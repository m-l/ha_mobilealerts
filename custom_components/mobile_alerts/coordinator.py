"""Data update coordinator for the MobileAlerts integration."""
from __future__ import annotations

import logging

import json

from homeassistant.components.mqtt import async_publish
from homeassistant.const import Platform
from mobilealerts import Gateway, MeasurementType, Sensor, SensorHandler

from .base import MobileAlertesBaseCoordinator
from .binary_sensor import create_binary_sensor_entities
from .const import (
    CONF_MODE,
    CONF_MQTT_TOPIC_PREFIX,
    DEFAULT_MQTT_TOPIC_PREFIX,
    MODE_ENTITIES,
    MODE_MQTT,
)
from .sensor import create_sensor_entities

_LOGGER = logging.getLogger(__name__)


_MQTT_KEY = {
    MeasurementType.HUMIDITY: "humidity",
    MeasurementType.AIR_PRESSURE: "airPressure",
    MeasurementType.CO2: "co2",
    MeasurementType.RAIN: "rain",
    MeasurementType.WIND_SPEED: "windSpeed",
    MeasurementType.GUST: "gustSpeed",
    MeasurementType.WIND_DIRECTION: "windDirection",
    MeasurementType.WETNESS: "wetness",
    MeasurementType.DOOR_WINDOW: "contact",
}


def _mqtt_key(measurement) -> str | None:
    """Map a measurement to its sarnau JSON key."""
    if measurement.type == MeasurementType.TEMPERATURE:
        return "temperature" if not measurement.prefix else "temperatureExt"
    return _MQTT_KEY.get(measurement.type)


class MobileAlertesDataCoordinator(MobileAlertesBaseCoordinator, SensorHandler):
    """Class to manage MobileAlerts data."""

    @property
    def gateway(self) -> Gateway:
        return self._gateway

    @property
    def _mode(self) -> str:
        return self._entry.options.get(CONF_MODE, MODE_ENTITIES)

    async def _publish_mqtt(self, sensor: Sensor) -> None:
        """Publish sensor readings as sarnau-compatible MQTT JSON."""
        payload: dict[str, list] = {}
        for measurement in sensor.measurements:
            key = _mqtt_key(measurement)
            if key is None or not isinstance(measurement.value, (int, float)):
                continue
            payload.setdefault(key, []).append(measurement.value)
        if not payload:
            return
        prefix = self._entry.options.get(
            CONF_MQTT_TOPIC_PREFIX, DEFAULT_MQTT_TOPIC_PREFIX
        )
        topic = f"{prefix}{sensor.sensor_id.lower()}/json"
        _LOGGER.debug("Publishing MQTT %s -> %s", topic, payload)
        await async_publish(self.hass, topic, json.dumps(payload), retain=True)

    async def sensor_added(self, sensor: Sensor) -> None:
        _LOGGER.debug("sensor_added %r", sensor)

        if self._mode == MODE_MQTT:
            await self._publish_mqtt(sensor)
            return

        binary_entity_component = self.hass.data[Platform.BINARY_SENSOR]
        binary_entity_platform = binary_entity_component._platforms.get(
            self._entry.entry_id, None
        )
        if binary_entity_platform is not None:
            self.hass.async_add_job(
                binary_entity_platform.async_add_entities(
                    create_binary_sensor_entities(self, sensor), True
                )
            )

        sensor_entity_component = self.hass.data[Platform.SENSOR]
        sensor_entity_platform = sensor_entity_component._platforms.get(
            self._entry.entry_id, None
        )
        if sensor_entity_platform is not None:
            self.hass.async_add_job(
                sensor_entity_platform.async_add_entities(
                    create_sensor_entities(self, sensor), True
                )
            )

        self.hass.config_entries.async_update_entry(self._entry)

    async def sensor_updated(self, sensor: Sensor) -> None:
        _LOGGER.debug("sensor_updated %r", sensor)
        if self._mode == MODE_MQTT:
            await self._publish_mqtt(sensor)
            return
        self.async_set_updated_data({})
