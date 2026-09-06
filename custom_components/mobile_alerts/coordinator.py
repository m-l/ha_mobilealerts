"""Data update coordinator for the MobileAlerts integration."""
from __future__ import annotations

import logging

import json
from datetime import datetime, timezone
from typing import Any

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


# Measurement types published as arrays (templates read index [0]).
_ARRAY_KEY = {
    MeasurementType.HUMIDITY: "humidity",
    MeasurementType.AIR_PRESSURE: "airPressure",
    MeasurementType.CO2: "co2",
    MeasurementType.RAIN: "rain",
}

# Measurement types published as scalars.
_SCALAR_KEY = {
    MeasurementType.WIND_SPEED: "windSpeed",
    MeasurementType.GUST: "gustSpeed",
    MeasurementType.WETNESS: "wetness",
    MeasurementType.DOOR_WINDOW: "contact",
}

_COMPASS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _compass(degrees: float) -> str:
    """Convert wind direction in degrees to a 16-point compass string."""
    return _COMPASS[int((degrees % 360) / 22.5 + 0.5) % 16]


# Rain sensor packet type (also the first byte of the sensor id).
_RAIN_SENSOR_TYPE = 0x08


def _event_time(value: int) -> int:
    """Decode a rain event time: top 2 bits select the scale, low 14 bits the count."""
    scale = (value >> 14) & 3
    value &= (1 << 14) - 1
    return value * (86400, 3600, 60, 1)[scale]


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
        payload: dict[str, Any] = {}
        for measurement in sensor.measurements:
            value = measurement.value
            if not isinstance(value, (int, float)):
                continue
            m_type = measurement.type
            if m_type == MeasurementType.TEMPERATURE:
                key = "temperature" if not measurement.prefix else "temperatureExt"
                payload.setdefault(key, []).append(value)
            elif m_type in _ARRAY_KEY:
                payload.setdefault(_ARRAY_KEY[m_type], []).append(value)
            elif m_type == MeasurementType.WIND_DIRECTION:
                payload["directionDegree"] = value
                payload["direction"] = _compass(value)
            elif m_type in _SCALAR_KEY:
                payload[_SCALAR_KEY[m_type]] = value
        if not payload:
            return

        # Per-sensor metadata (maserver-compatible keys)
        payload["id"] = sensor.sensor_id.lower()
        payload["battery"] = "low" if sensor.low_battery else "ok"
        payload["offline"] = False
        if sensor.timestamp:
            payload["t"] = datetime.fromtimestamp(
                sensor.timestamp, timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        if sensor.update_period:
            payload["lastTransmit"] = sensor.update_period
        if sensor.by_event is not None:
            payload["by_event"] = bool(sensor.by_event)
        payload["counter"] = sensor.counter
        payload["model"] = sensor.model
        payload["name"] = sensor.name

        # Rain sensors: expose the raw event counter and event times parsed
        # straight from the packet, which the library does not surface (needed
        # for rain-gauge templates). Layout follows MMMMobileAlerts ID08.
        raw = sensor.last_update
        if (
            isinstance(raw, (bytes, bytearray))
            and len(raw) >= 36
            and raw[6] == _RAIN_SENSOR_TYPE
        ):
            body = raw[14:]
            payload["eventCounter"] = int.from_bytes(body[2:4], "big")
            payload["eventTimes"] = [
                _event_time(int.from_bytes(body[4 + 2 * i : 6 + 2 * i], "big"))
                for i in range(9)
            ]

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
