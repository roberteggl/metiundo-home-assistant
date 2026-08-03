"""Manual historical data import service action."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from custom_components.metiundo.api import MetiundoApiClientError
from custom_components.metiundo.const import ATTR_END_DATE, ATTR_START_DATE, LOGGER
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from custom_components.metiundo.data import MetiundoConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse


async def async_handle_import_historical_data(
    hass: HomeAssistant,
    entry: MetiundoConfigEntry,
    call: ServiceCall,
) -> ServiceResponse:
    """Import a selected historical date range for one config entry."""
    start_date = call.data[ATTR_START_DATE]
    end_date = call.data.get(ATTR_END_DATE)
    if not isinstance(start_date, date) or (end_date is not None and not isinstance(end_date, date)):
        raise ServiceValidationError("The historical import dates are invalid")

    start_time = dt_util.now()
    try:
        result = await entry.runtime_data.coordinator.async_import_historical_data(start_date, end_date)
    except ValueError as exception:
        raise ServiceValidationError(str(exception)) from exception
    except (ConfigEntryAuthFailed, ConfigEntryNotReady, MetiundoApiClientError, UpdateFailed) as exception:
        LOGGER.error("Historical data import failed: %s", exception)
        return {
            "status": "error",
            "timestamp": dt_util.now().isoformat(),
            "duration_ms": round((dt_util.now() - start_time).total_seconds() * 1000, 2),
            "error": str(exception),
            "error_type": type(exception).__name__,
        }

    return {
        "status": "success",
        "timestamp": dt_util.now().isoformat(),
        "duration_ms": round((dt_util.now() - start_time).total_seconds() * 1000, 2),
        **result,
    }
