# Home Assistant support for Mobile-Alerts

## Overview

This integration supports various Mobile-Alerts sensors. The integration acts as proxy server between Mobile-Alerts gateway and cloud. 

Readings can be exposed either as **native Home Assistant entities** or through an **MQTT gateway** mode that republishes them in the sarnau/MMMMobileAlerts JSON format, so an existing `mqtt:` sensor configuration (or a standalone maserver setup) keeps working unchanged.

_Based on MMMMobileAlerts by [@sarnau](https://github.com/sarnau/MMMMobileAlerts)

## Installation

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Alternatively install via [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=m-l&repository=ha_mobilealerts&category=integration)

## Configuration

The gateway is discovered automatically (UDP broadcast and DHCP). Add the integration from **Settings → Devices & Services → Add Integration → Mobile-Alerts**. Home Assistant and the gateway must be on the same subnet for discovery to succeed.

Once added, open the integration's **Configure** dialog to choose how readings are exposed and whether data is still forwarded to the Mobile-Alerts cloud. Changes are applied immediately (the config entry reloads automatically).

### Modes

**Native Home Assistant entities** (default) — each measurement becomes a Home Assistant `sensor` / `binary_sensor` entity.

**MQTT gateway (sarnau-compatible)** — each sensor's readings are published as a single JSON document to:

```
<mqtt_topic_prefix><sensor_id>/json
```

The topic prefix defaults to `/MobileAlerts/` and `<sensor_id>` is lower-case, matching the topic layout of [MMMMobileAlerts](https://github.com/sarnau/MMMMobileAlerts) / maserver. This lets the integration replace a standalone maserver while your existing `mqtt:` sensors continue to work.

The broker connection is **not** configured here — messages are published through Home Assistant's own MQTT integration, so the broker host, port and credentials live there. The MQTT integration must be set up for this mode to work.

#### Payload

Environmental measurements are published as **arrays** (templates read index `0`); wind values and all metadata are **scalars**. Each message also carries per-sensor metadata:

```json
{
  "temperature": [21.3],
  "humidity": [55],
  "temperatureExt": [12.1],
  "windSpeed": 0.2,
  "gustSpeed": 1.0,
  "directionDegree": 90,
  "direction": "E",
  "battery": "ok",
  "offline": false,
  "id": "094596df5368",
  "t": "2022-09-15T06:27:50.000Z",
  "lastTransmit": 360,
  "by_event": false,
  "counter": 54242,
  "model": "MA10238",
  "name": "Air pressure monitor (...)"
}
```

| Key | Type | Notes |
| --- | --- | --- |
| `temperature`, `temperatureExt`, `humidity`, `airPressure`, `co2`, `rain` | array | Index `0` is the current value. `temperatureExt` is a second/external probe (pool, water). |
| `windSpeed`, `gustSpeed` | scalar | m/s |
| `directionDegree` | scalar | Wind direction in degrees |
| `direction` | scalar | 16-point compass string (`N`, `NNE`, ...) |
| `wetness`, `contact` | scalar | Leakage / door-window sensors |
| `eventCounter` | scalar | Rain sensors: cumulative bucket-tip counter |
| `eventTimes` | array | Rain sensors: seconds since each of the last 9 events (`[0]` is the most recent; `0` = an event in this transmission) |
| `battery` | scalar | `"ok"` or `"low"` |
| `t` | scalar | Reading time, ISO 8601 UTC |
| `lastTransmit` | scalar | Sensor transmit interval, seconds |
| `id` | scalar | Sensor id (also in the topic) |
| `by_event` | scalar | `true` if triggered by an event rather than a scheduled report |
| `counter` | scalar | Packet counter |
| `offline` | scalar | Always `false` — see note below |
| `model`, `name` | scalar | Sensor model / name |

> **`offline`:** the integration publishes only when a sensor transmits, so `offline` is always `false` (there is no watchdog that flips it to `true` after silence — use the age of `t` for staleness instead). Rain sensors additionally publish `eventCounter` and `eventTimes`, parsed directly from the packet, so rain-gauge templates that count bucket tips work as they did with maserver.

Example `mqtt:` sensor reusing the published data:

```yaml
mqtt:
  sensor:
    - state_topic: "/MobileAlerts/094596df5368/json"
      name: "Garage Temperature"
      value_template: "{{ value_json.temperature[0] | float }}"
      unit_of_measurement: "°C"
    - state_topic: "/MobileAlerts/094596df5368/json"
      name: "Garage Humidity"
      value_template: "{{ value_json.humidity[0] | float }}"
      unit_of_measurement: "%"
```

Battery (and, if you want it, a staleness check based on the age of `t`) as binary sensors:

```yaml
mqtt:
  binary_sensor:
    - state_topic: "/MobileAlerts/094596df5368/json"
      name: "Garage sensor battery"
      device_class: battery
      value_template: "{{ 'ON' if value_json.battery == 'low' else 'OFF' }}"
```

### Send data to cloud

When enabled (default), the integration forwards received data to the Mobile-Alerts cloud so the official app keeps working. Disable it to keep everything local.

## Credits

- Protocol and JSON format: [MMMMobileAlerts](https://github.com/sarnau/MMMMobileAlerts) by [@sarnau](https://github.com/sarnau)
- Original Home Assistant integration: [@PlusPlus-ua](https://github.com/PlusPlus-ua/ha_mobilealerts)
- Home Assistant 2024.x compatibility: [@greiter](https://github.com/greiter), [@Silver-Volt4](https://github.com/Silver-Volt4), [@msvb04](https://github.com/msvb04)

