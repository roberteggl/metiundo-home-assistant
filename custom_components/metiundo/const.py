"""Constants for Metiundo Smart Meter."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN = "metiundo"
ATTRIBUTION = "Data provided by Metiundo"
MANUFACTURER = "Metiundo"

# API endpoint
API_BASE_URL = "https://api.metiundo.de/v1"
PORTAL_URL = "https://portal.metiundo.de"
API_TIMEOUT_SECONDS = 10

# Config entry data keys
CONF_METERING_POINT_UUID = "metering_point_uuid"
CONF_ENABLE_EXPORT_METRICS = "enable_export_metrics"
CONF_IMPORT_HISTORICAL_DATA = "import_historical_data"
CONF_HISTORY_START_DATE = "history_start_date"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"
ISSUE_HISTORICAL_IMPORT_FAILED = "historical_import_failed"
ISSUE_NO_RECENT_DATA = "no_recent_data"

# Platform parallel updates - applied to all platforms
PARALLEL_UPDATES = 1

# Default configuration values
DEFAULT_UPDATE_INTERVAL_HOURS = 24
READINGS_LOOKBACK_HOURS = 48
INITIAL_HISTORY_CHUNK_DAYS = 31
DEFAULT_ENABLE_DEBUGGING = False
DEFAULT_ENABLE_EXPORT_METRICS = True
