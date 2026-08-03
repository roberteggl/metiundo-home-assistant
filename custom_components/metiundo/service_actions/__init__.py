"""Service actions package for metiundo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.metiundo.const import DOMAIN, LOGGER
from custom_components.metiundo.service_actions.reload_data import async_handle_reload_data
from homeassistant.core import ServiceCall

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# Service action names - only used within service_actions module
SERVICE_RELOAD_DATA = "reload_data"


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

    # Register services (only once at component level)
    if not hass.services.has_service(DOMAIN, SERVICE_RELOAD_DATA):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RELOAD_DATA,
            handle_reload_data,
        )

    LOGGER.debug("Services registered for %s", DOMAIN)
