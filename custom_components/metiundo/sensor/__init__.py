"""Sensor platform for metiundo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.metiundo.const import (
    CONF_ENABLE_EXPORT_METRICS,
    DEFAULT_ENABLE_EXPORT_METRICS,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)

from .energy import ENTITY_DESCRIPTIONS as ENERGY_ENTITY_DESCRIPTIONS, MetiundoEnergySensor
from .reading import ENTITY_DESCRIPTIONS as READING_ENTITY_DESCRIPTIONS, MetiundoReadingMetadataSensor

if TYPE_CHECKING:
    from custom_components.metiundo.data import MetiundoConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MetiundoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator
    if coordinator.data is None:
        return

    available_fields = coordinator.data.metering_point.available_fields
    export_metrics_enabled = entry.options.get(
        CONF_ENABLE_EXPORT_METRICS,
        DEFAULT_ENABLE_EXPORT_METRICS,
    )
    energy_entities = (
        MetiundoEnergySensor(coordinator, entity_description)
        for entity_description in ENERGY_ENTITY_DESCRIPTIONS
        if (entity_description.key == "grid_import_energy" and "energyOut" in available_fields)
        or (
            entity_description.key == "grid_export_energy" and "energyIn" in available_fields and export_metrics_enabled
        )
    )
    reading_entities = (
        MetiundoReadingMetadataSensor(coordinator, entity_description)
        for entity_description in READING_ENTITY_DESCRIPTIONS
    )
    async_add_entities([*energy_entities, *reading_entities])
