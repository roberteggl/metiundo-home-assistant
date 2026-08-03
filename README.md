# Metiundo Smart Meter

> [!NOTE]
> This is an independent, community-maintained integration and is not affiliated with,
> endorsed by, or supported by Metiundo.

## Features

- **Easy setup** through the UI - no YAML required
- **Grid import / export energy**: Cumulative smart meter readings (OBIS 1.8.0 / 2.8.0)
- **15-minute historical readings** from the Metiundo API
- **Energy Dashboard-compatible** grid import/export sensors
- **Reconfigurable** credentials and **options flow** (update interval, debug logging)
- **Diagnostics**: API connection status and integration statistics

> [!IMPORTANT]
> This integration reads **historical** meter data from the Metiundo API. It does **not**
> provide real-time power readings. Data is available in 15-minute intervals, but new API
> batches are typically published every 24 hours.

## Installation

### HACS

This integration is not yet included in the default HACS store. Add it as a custom
repository:

1. Open **HACS** in Home Assistant.
2. Open the **three-dot menu** in the top-right corner.
3. Select **Custom repositories**.
4. Enter `https://github.com/roberteggl/metiundo-home-assistant`.
5. Select **Integration** as the repository type and click **Add**.
6. Search for **Metiundo Smart Meter** in HACS and install it.

Updates are published through the [GitHub releases](https://github.com/roberteggl/metiundo-home-assistant/releases).

### Manual

1. Download the `custom_components/metiundo/` folder from this repository
2. Copy it to your Home Assistant's `custom_components/` directory
3. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"** → search for "Metiundo Smart Meter"
3. Enter your Metiundo account **email address** and **password**
4. Select the electricity metering point to expose
5. Click **Submit**

The integration validates your credentials and starts loading your data.

### Options

Adjust settings anytime by clicking **Configure** on the integration:

| Name            | Default  | Description                              |
| --------------- | -------- | ---------------------------------------- |
| Update Interval | 24 hours | How often to refresh the daily API batch |
| Debug Logging   | Off      | Enable extra debug logging               |
| Export Metrics  | On       | Create the grid export energy sensor     |

During initial setup, you can select **Import data older than the last 48 hours** and choose
an earliest date. Readings from that date onward are fetched in API-sized chunks and
imported into Home Assistant's long-term energy statistics. The option is consumed after
the first successful refresh and does not run again on future reloads.

## Entities

| Platform        | Description                                             |
| --------------- | ------------------------------------------------------- |
| `sensor`        | Cumulative import/export energy and reading diagnostics |
| `binary_sensor` | API connection status                                   |

- **API Connection**: On when connected and receiving data, off when the connection is lost or authentication failed. Attributes show the selected metering point, reading timestamp, update interval, and API endpoint.

## Service

### `metiundo.reload_data`

Manually refresh data from the API without waiting for the update interval:

```yaml
action: metiundo.reload_data
```

### `metiundo.import_historical_data`

Import a selected date range without removing and re-adding the integration:

```yaml
action: metiundo.import_historical_data
data:
  config_entry_id: "YOUR_CONFIG_ENTRY_ID"
  start_date: "2024-01-01"
```

The optional `end_date` defaults to the latest available reading. The action returns
the number of API chunks, readings, and statistics imported. Overlapping historical
data is safe to re-import.

## Troubleshooting

### Reauthentication

If your credentials expire or change, Home Assistant will automatically prompt you to reauthenticate:

1. Go to **Settings** → **Devices & Services**
2. Look for **"Action Required"** or **"Configuration Required"** on the integration
3. Click **"Reconfigure"** or follow the prompt
4. Enter your updated credentials and click **Submit**

You can also update credentials at any time via the **three-dot menu** → **Reconfigure**.

### Debug Logging

Add this to `configuration.yaml`, restart, and reproduce the issue:

```yaml
logger:
  default: info
  logs:
    custom_components.metiundo: debug
```

### Data Not Updating

1. Check the **API Connection** binary sensor - it should be "On"
2. Verify your network connection and credentials
3. Download integration diagnostics (Settings → Devices & Services → Metiundo Smart Meter → three-dot menu → Download diagnostics)

## Contributing

Contributions are welcome! Please open an issue or pull request if you have suggestions or improvements.

For development setup and validation, see the [development docs](docs/development/).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
