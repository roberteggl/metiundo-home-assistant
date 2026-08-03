"""Service actions package for metiundo."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol

from custom_components.metiundo.const import ATTR_END_DATE, ATTR_START_DATE, DOMAIN, LOGGER
from custom_components.metiundo.service_actions.import_historical_data import async_handle_import_historical_data
from custom_components.metiundo.service_actions.reload_data import async_handle_reload_data
from homeassistant import config_entries
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

if TYPE_CHECKING:
    from custom_components.metiundo.data import MetiundoConfigEntry
    from homeassistant.core import HomeAssistant, ServiceResponse

# Service action names - only used within service_actions module
SERVICE_RELOAD_DATA = "reload_data"
SERVICE_IMPORT_HISTORICAL_DATA = "import_historical_data"

SERVICE_IMPORT_HISTORICAL_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_START_DATE): cv.date,
        vol.Optional(ATTR_END_DATE): cv.date,
    },
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """
    Register services for the integration.

    Services are registered at component level (in async_setup) rather than
    per config entry. This is a Silver Quality Scale requirement and ensures:
    - Service validation works correctly
    - Services are available even without config entries
    - Helpful error messages are provided

    Service handlers iterate over all config entries to find the relevant one.
    """

    async def handle_reload_data(call: ServiceCall) -> None:
        """Handle the reload_data service call."""
        # Find all config entries for this domain
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            LOGGER.warning("No config entries found for %s", DOMAIN)
            return

        # Reload data for all entries
        for entry in entries:
            await async_handle_reload_data(hass, entry, call)

    async def handle_import_historical_data(call: ServiceCall) -> ServiceResponse:
        """Handle a targeted historical data import."""
        entry = hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY_ID])
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError("The selected Metiundo config entry was not found")
        if entry.state is not config_entries.ConfigEntryState.LOADED:
            raise ServiceValidationError("The selected Metiundo config entry is not loaded")
        return await async_handle_import_historical_data(
            hass,
            cast("MetiundoConfigEntry", entry),
            call,
        )

    # Register services (only once at component level)
    if not hass.services.has_service(DOMAIN, SERVICE_RELOAD_DATA):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RELOAD_DATA,
            handle_reload_data,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_IMPORT_HISTORICAL_DATA):
        hass.services.async_register(
            DOMAIN,
            SERVICE_IMPORT_HISTORICAL_DATA,
            handle_import_historical_data,
            schema=SERVICE_IMPORT_HISTORICAL_DATA_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    LOGGER.debug("Services registered for %s", DOMAIN)
