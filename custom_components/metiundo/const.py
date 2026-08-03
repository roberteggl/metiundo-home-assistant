"""Constants for Metiundo Smart Meter."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN = "metiundo"
ATTRIBUTION = "Data provided by Metiundo"
MANUFACTURER = "Metiundo"

# API endpoint
API_BASE_URL = "https://api.metiundo.de"

# Platform parallel updates - applied to all platforms
PARALLEL_UPDATES = 1

# Default configuration values
DEFAULT_UPDATE_INTERVAL_HOURS = 1
DEFAULT_ENABLE_DEBUGGING = False
