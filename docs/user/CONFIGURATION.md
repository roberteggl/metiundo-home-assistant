# Configuration Reference

This document describes all configuration options and settings available in the Metiundo Smart Meter custom integration.

## Integration Configuration

### Initial Setup Options

These options are configured during initial setup via the Home Assistant UI.

#### Account Settings

| Option       | Type   | Required | Default | Description                    |
| ------------ | ------ | -------- | ------- | ------------------------------ |
| **Username** | string | Yes      | -       | Your Metiundo account username |
| **Password** | string | Yes      | -       | Your Metiundo account password |

### Options Flow (Reconfiguration)

After initial setup, you can modify settings:

1. Go to **Settings** → **Devices & Services**
2. Find "Metiundo Smart Meter"
3. Click **Configure**
4. Modify settings
5. Click **Submit**

**Available options:**

| Option              | Type    | Default | Description                                       |
| ------------------- | ------- | ------- | ------------------------------------------------- |
| **Update Interval** | number  | 1 h     | How often to refresh data (0.25–24 hours)         |
| **Debug Logging**   | boolean | Off     | Enable detailed debug logging for troubleshooting |

## Services

The integration provides the following service:

### `metiundo.reload_data`

Force a refresh of the integration data from the API.

**Example:**

```yaml
service: metiundo.reload_data
```

### Using Services in Automations

```yaml
automation:
  - alias: "Refresh Metiundo data in the morning"
    trigger:
      - trigger: time
        at: "06:00:00"
    action:
      - action: metiundo.reload_data
```

## Polling Behavior

The integration uses polling to fetch updates from the Metiundo API:

- **Default interval:** 1 hour
- **Minimum interval:** 15 minutes
- **Maximum interval:** 24 hours

The Metiundo API provides historical data in 15-minute intervals. A shorter
update interval does not increase data resolution — it only updates the local
state more often.

## Diagnostic Data

The integration provides diagnostic data for troubleshooting:

1. Go to **Settings** → **Devices & Services**
2. Find "Metiundo Smart Meter"
3. Click on the device
4. Click **Download Diagnostics**

Diagnostic data includes:

- Connection status
- Update interval
- Config entry and integration information
- Entity and device information

**Privacy note:** Diagnostic data may contain sensitive information. Review before sharing.

## Troubleshooting Configuration

### Config Entry Fails to Load

If the integration fails to load after configuration:

1. Check Home Assistant logs for errors
2. Verify credentials are correct
3. Test connectivity to `api.metiundo.de` from Home Assistant
4. Try removing and re-adding the integration

### Options Don't Save

If configuration changes aren't persisted:

1. Check for validation errors in the UI
2. Ensure values are within allowed ranges
3. Review logs for detailed error messages
4. Try restarting Home Assistant

## Related Documentation

- [Getting Started](./GETTING_STARTED.md) - Installation and initial setup
- [Examples](./EXAMPLES.md) - Automation and dashboard examples
- [GitHub Issues](https://github.com/Robert27/homeassistant-metiundo/issues) - Report problems
