# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [0.2.2] - 2026-09-06

### Changed

- Documentation: README now covers the native-entities and MQTT gateway modes, the `<prefix><sensor_id>/json` topic layout, the JSON payload format and an example `mqtt:` sensor configuration, plus a credits section. HACS repository badge points at this fork.

## [0.2.1] - 2026-09-06

### Fixed

- Proxy diagnostic now reports the live proxy target (`gateway.proxy`) instead of the preserved original setting (`orig_proxy`), which previously showed the address of a prior/external proxy server (e.g. a former maserver).

## [0.2.0] - 2026-09-06

### Added

- **MQTT gateway mode**: publish sensor readings as sarnau/MMMMobileAlerts-compatible JSON to `<prefix><sensor_id>/json` (default prefix `/MobileAlerts/`, lower-case id) instead of creating native entities, selectable from the options flow. Enables drop-in replacement of a standalone maserver while reusing existing `mqtt:` sensors.
- Configurable MQTT topic prefix in the options flow.
- Automatic reload of the config entry when options change, so mode and cloud-forwarding changes apply without a manual reload.

### Fixed

- Options flow crashed on import on Home Assistant 2024.11+ (and later cores) due to an invalid `config_entry` setter in the options handler. Removed the self-managed `config_entry` and rely on the framework-provided property.

### Changed

- `manifest.json`: added `mqtt` to `after_dependencies`.

## [0.1.4] - 2025-07-10

### Changed

Fix compatibility with frozen dataclasses for Home Assistant 2024.x

- Refactor entity descriptions to use dataclasses.replace instead of direct attribute assignment
- Prevent FrozenInstanceError on Sensor and BinarySensor entities
- Clean up legacy code and ensure compatibility with latest Home Assistant core

## [0.1.3] - 2023-04-20

### Changed

- Improved handling of rain sensor.
