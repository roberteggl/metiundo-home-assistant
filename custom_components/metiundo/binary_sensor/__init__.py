"""Binary sensor platform for metiundo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.metiundo.const import PARALLEL_UPDATES as PARALLEL_UPDATES

from .connectivity import ENTITY_DESCRIPTIONS as CONNECTIVITY_DESCRIPTIONS, MetiundoConnectivitySensor

if TYPE_CHECKING:
    from custom_components.metiundo.data import MetiundoConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MetiundoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    async_add_entities(
        MetiundoConnectivitySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in CONNECTIVITY_DESCRIPTIONS
    )
