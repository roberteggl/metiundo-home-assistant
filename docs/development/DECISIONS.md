# Architectural and Design Decisions

This document records significant architectural and design decisions made during the development of this integration.

## Format

Each decision is documented with:

- **Date:** When the decision was made
- **Context:** Why this decision was necessary
- **Decision:** What was decided
- **Rationale:** Why this approach was chosen
- **Consequences:** Expected impacts and trade-offs

______________________________________________________________________

## Decision Log

### Integration Type: Service (Cloud API)

**Date:** 2026-08-03 (Metiundo initialization)

**Context:** Metiundo is a cloud service exposing smart meter data via a REST API
(`https://api.metiundo.de`). There is no local device to discover.

**Decision:** Treat the integration as a `service`-type integration with `integration_type: hub`
in the manifest, configured via config flow with Metiundo account credentials. Single account
per config entry; the account username serves as the unique ID.

**Rationale:**

- Cloud service requires user-supplied credentials, not discovery
- One config entry per Metiundo account matches the API's data model
- Config flow (not YAML) is the modern Home Assistant standard (ADR-0010)

**Consequences:**

- No discovery support (bluetooth/zeroconf/etc.)
- Reauth flow required for expired credentials
- Reconfigure flow for credential updates

______________________________________________________________________

### Data Model: Historical 15-Minute Readings

**Date:** 2026-08-03 (Metiundo initialization)

**Context:** The Metiundo API exposes historical meter readings in 15-minute intervals:
cumulative grid import (`energyOut`, OBIS 1.8.0) and export (`energyIn`, OBIS 2.8.0),
each with a timestamp and data-quality information. It is NOT a live-power API.

**Decision:** Model the integration around these historical readings. Expose cumulative
energy as Energy Dashboard-compatible sensors. Do not imply real-time power readings.

**Rationale:**

- Matches the API's actual capabilities
- Cumulative energy values are the correct basis for the Energy Dashboard
- Avoids misleading users with fake "current power" sensors

**Consequences:**

- Planned sensors: grid import/export energy (kWh), calculated 15-minute average power (kW)
- Optionally support historical-statistics import for the long-term statistics dashboard
- Update interval minimum is 15 minutes (matches data resolution)

______________________________________________________________________

### Use DataUpdateCoordinator for All Data Fetching

**Date:** 2025-11-29 (Template initialization)

**Context:** The integration needs to fetch data from an external API and share it with multiple entities. Home Assistant provides several patterns for this.

**Decision:** Use `DataUpdateCoordinator` from `homeassistant.helpers.update_coordinator` as the central data management component.

**Rationale:**

- Provides built-in support for update intervals and error handling
- Automatic retry with exponential backoff
- Shared data access prevents duplicate API calls
- Standard pattern recommended by Home Assistant
- Entities automatically become unavailable when coordinator fails

**Consequences:**

- All entities must inherit from `CoordinatorEntity`
- Single update interval applies to all entities
- Data is fetched even if no entities are enabled
- Coordinator manages entity lifecycle and availability

______________________________________________________________________

### Separate API Client from Coordinator

**Date:** 2025-11-29 (Template initialization)

**Context:** The coordinator needs to fetch data, but business logic should be separated from data transport.

**Decision:** Implement API communication in separate `api/client.py` module, coordinator only orchestrates updates.

**Rationale:**

- Separation of concerns: transport vs. orchestration
- Easier to test API client in isolation
- Simpler to swap API implementation if needed
- Clearer error handling boundaries

**Consequences:**

- Additional abstraction layer
- Coordinator depends on API client
- API client raises custom exceptions for error translation

______________________________________________________________________

### Platform-Specific Directories

**Date:** 2025-11-29 (Template initialization)

**Context:** Integration supports multiple platforms (sensor, binary_sensor, etc.).

**Decision:** Each platform gets its own directory with individual entity files.

**Rationale:**

- Clear organization as integration grows
- Easier to find specific entity implementations
- Supports multiple entities per platform cleanly
- Follows Home Assistant Core pattern

**Consequences:**

- More files/directories than single-file approach
- Platform `__init__.py` must import and register entities
- Slightly more initial setup overhead

______________________________________________________________________

### EntityDescription for Static Metadata

**Date:** 2025-11-29 (Template initialization)

**Context:** Entities have static metadata (name, icon, device class) that doesn't change.

**Decision:** Use `EntityDescription` dataclasses to define static entity metadata.

**Rationale:**

- Declarative and easy to read
- Type-safe with dataclasses
- Recommended Home Assistant pattern
- Separates static configuration from dynamic behavior

**Consequences:**

- Each entity type needs an EntityDescription
- Dynamic entities need custom handling
- Static and dynamic properties clearly separated

______________________________________________________________________

## Future Considerations

### Polling vs. Push

**Status:** Uses polling

Currently implements polling-based updates. The Metiundo API provides historical data in
15-minute intervals, so push/WebSocket updates are not applicable — the data source itself
is not real-time.

______________________________________________________________________

### State Restoration

**Status:** Not yet implemented

Consider implementing state restoration for configurable settings to maintain state across
Home Assistant restarts when the API is unavailable. Not relevant for read-only energy sensors.

______________________________________________________________________

## Decision Review

These decisions should be reviewed periodically (suggested: quarterly or when major features are added) to ensure they still serve the integration's needs.
