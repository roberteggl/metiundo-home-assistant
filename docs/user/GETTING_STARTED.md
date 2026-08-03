# Getting Started with Metiundo Smart Meter

This guide will help you install and set up the Metiundo Smart Meter custom integration for Home Assistant.

## Prerequisites

- Home Assistant 2026.4.0 or newer
- HACS (Home Assistant Community Store) installed
- A Metiundo account with access to the Metiundo API
- Network connectivity to `api.metiundo.de`

> [!NOTE]
> This integration is not yet released. It will be available through HACS once the
> first version is published. Until then, use manual installation.

## Installation

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/Robert27/homeassistant-metiundo/releases)
2. Extract the `metiundo` folder from the archive
3. Copy it to `custom_components/metiundo/` in your Home Assistant configuration directory
4. Restart Home Assistant

## Initial Setup

After installation, add the integration:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Metiundo Smart Meter"
4. Enter your Metiundo account credentials:
   - **Username:** Your Metiundo username
   - **Password:** Your Metiundo password
5. Click **Submit**

The integration validates your credentials and starts loading your smart meter data.

> [!IMPORTANT]
> This integration reads **historical** meter data from the Metiundo API in
> 15-minute intervals. It does **not** provide real-time power readings.

## What Gets Created

After successful setup, the integration creates:

### Entities

- **Binary Sensor:** API connection status (`binary_sensor.*_api_connectivity`)

Energy sensors (cumulative grid import/export) will be added in a future release.

## First Steps

### Dashboard Cards

Add entities to your dashboard:

1. Go to your dashboard
2. Click **Edit Dashboard** → **Add Card**
3. Choose card type (e.g., "Entities", "Glance")
4. Select entities from "Metiundo Smart Meter"

Example entities card:

```yaml
type: entities
title: Metiundo Smart Meter
entities:
  - binary_sensor.metiundo_smart_meter_api_connectivity
```

### Automations

Use the integration in automations:

**Example - Notify on connection loss:**

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
          message: "The connection to the Metiundo API was lost."
```

## Troubleshooting

### Connection Failed

If setup fails with connection errors:

1. Verify your username and password are correct
2. Check network connectivity to `api.metiundo.de`
3. Check Home Assistant logs for detailed error messages

### Entities Not Updating

If entities show "Unavailable" or don't update:

1. Check the **API Connection** binary sensor - it should be "On"
2. Verify API credentials haven't expired
3. Review logs: **Settings** → **System** → **Logs**
4. Try reloading the integration

### Debug Logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: warning
  logs:
    custom_components.metiundo: debug
```

Add this to `configuration.yaml`, restart, and reproduce the issue. Check logs for detailed information.

## Next Steps

- See [CONFIGURATION.md](./CONFIGURATION.md) for detailed configuration options
- See [EXAMPLES.md](./EXAMPLES.md) for more automation examples
- Report issues at [GitHub Issues](https://github.com/Robert27/homeassistant-metiundo/issues)

## Support

For help and discussion:

- [GitHub Discussions](https://github.com/Robert27/homeassistant-metiundo/discussions)
- [Home Assistant Community Forum](https://community.home-assistant.io/)
