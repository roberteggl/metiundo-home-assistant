"""Service action handlers for metiundo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.metiundo.const import DOMAIN, LOGGER
from homeassistant.exceptions import ConfigEntryAuthFailed, ServiceValidationError

if TYPE_CHECKING:
    from custom_components.metiundo.data import MetiundoConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall


async def async_handle_reload_data(
    _hass: HomeAssistant,
    entry: MetiundoConfigEntry,
    _call: ServiceCall,
) -> None:
    """
    Force a coordinator refresh for one config entry.

    ``async_request_refresh`` only schedules work and never raises update failures,
    so this awaits ``async_refresh`` and reports the outcome via the coordinator.
    """
    LOGGER.info("Reload data service called for entry %s", entry.entry_id)

    coordinator = entry.runtime_data.coordinator
    try:
        await coordinator.async_refresh()
    except ConfigEntryAuthFailed as exception:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="authentication_failed",
        ) from exception

    if not coordinator.last_update_success:
        error = coordinator.last_exception or "Unknown error"
        raise ServiceValidationError(f"Failed to reload Metiundo data: {error}")

    LOGGER.info("Data reload completed successfully for entry %s", entry.entry_id)
