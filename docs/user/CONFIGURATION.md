# Configuration Reference

This document describes all configuration options and settings available in the Metiundo Smart Meter custom integration.

## Integration Configuration

### Initial Setup Options

These options are configured during initial setup via the Home Assistant UI.

#### Account Settings

| Option            | Type   | Required | Default | Description                         |
| ----------------- | ------ | -------- | ------- | ----------------------------------- |
| **Email address** | string | Yes      | -       | Your Metiundo account email address |
| **Password**      | string | Yes      | -       | Your Metiundo account password      |

If the account has multiple supported electricity metering points, the setup flow asks you
to select one. One config entry exposes one selected metering point.

### Options Flow (Reconfiguration)

After initial setup, you can modify settings:

1. Go to **Settings** → **Devices & Services**
2. Find "Metiundo Smart Meter"
3. Click **Configure**
4. Modify settings
5. Click **Submit**

**Available options:**

| Option              | Type    | Default | Description                                              |
| ------------------- | ------- | ------- | -------------------------------------------------------- |
| **Update Interval** | number  | 24 h    | How often to refresh the daily API batch (0.25–24 hours) |
| **Debug Logging**   | boolean | Off     | Enable detailed debug logging for troubleshooting        |
| **Export Metrics**  | boolean | On      | Create the grid export energy sensor                     |

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

- **Default interval:** 24 hours
- **Minimum interval:** 15 minutes
- **Maximum interval:** 24 hours

The Metiundo API publishes a daily batch containing historical data in 15-minute
intervals. A shorter update interval does not increase data resolution — it only
requests the same batch more often.

### Initial History Import

During initial setup, the integration can fetch historical readings from a date selected by
the user. The request is split into smaller ranges and imported into Home Assistant's
long-term energy statistics. This option is consumed after the first successful refresh and
is not available as a recurring polling setting.

## Diagnostic Data

### Manual Historical Import

Use the `metiundo.import_historical_data` action to import a date range after initial
setup. Select the Metiundo config entry and a start date; the end date is optional and
defaults to the latest available reading. The action fetches data in chunks and returns
import counts in its response.

```yaml
action: metiundo.import_historical_data
data:
  config_entry_id: "YOUR_CONFIG_ENTRY_ID"
  start_date: "2024-01-01"
```

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

The metering-point address, MeLo ID, and MaLo consumption/production IDs are
available as diagnostic sensors but are disabled by default because they may
contain sensitive location or market-participant information. Enable them from
the device's entity settings when needed.

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
- [GitHub Issues](https://github.com/roberteggl/metiundo-home-assistant/issues) - Report problems
