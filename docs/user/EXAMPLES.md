# Examples

This page provides ready-to-use examples for automations and dashboards
with the Metiundo Smart Meter custom integration.

Replace entity IDs like `binary_sensor.metiundo_smart_meter_*` with your actual
entity IDs after setting up the integration.

> [!NOTE]
> Energy sensors (grid import/export) are planned for a future release. Once
> available, you can use them in the Home Assistant Energy Dashboard.

## Automations

### Notify when the API connection is lost

```yaml
automation:
  - alias: "Notify on Metiundo connection loss"
    trigger:
      - trigger: state
        entity_id: binary_sensor.metiundo_smart_meter_api_connectivity
        to: "off"
        for:
          minutes: 5
    action:
      - action: notify.notify
        data:
          title: "Metiundo connection lost"
          message: "The connection to the Metiundo API was lost."
```

### Refresh data on a schedule

```yaml
automation:
  - alias: "Refresh Metiundo data every morning"
    trigger:
      - trigger: time
        at: "06:00:00"
    action:
      - action: metiundo.reload_data
```

## Dashboard Cards

### Device summary — entities card

```yaml
type: entities
title: Metiundo Smart Meter
entities:
  - entity: binary_sensor.metiundo_smart_meter_api_connectivity
    name: Connected
```

### Status badge — multiple entities

```yaml
type: glance
title: Metiundo Smart Meter
entities:
  - entity: binary_sensor.metiundo_smart_meter_api_connectivity
    name: Online
show_state: true
```

## Related Documentation

- [Configuration Reference](./CONFIGURATION.md) - All configuration options
- [Getting Started](./GETTING_STARTED.md) - Installation and initial setup
- [GitHub Issues](https://github.com/Robert27/homeassistant-metiundo/issues) - Report problems
