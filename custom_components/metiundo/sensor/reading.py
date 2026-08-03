"""Diagnostic sensors for reading metadata."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from custom_components.metiundo.entity import MetiundoEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.metiundo.coordinator import MetiundoDataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="last_reading_time",
        translation_key="last_reading_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
    ),
    SensorEntityDescription(
        key="reading_quality",
        translation_key="reading_quality",
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
    ),
    SensorEntityDescription(
        key="metering_point_address",
        translation_key="metering_point_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_entity_name=True,
    ),
    SensorEntityDescription(
        key="melo",
        translation_key="melo",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_entity_name=True,
    ),
    SensorEntityDescription(
        key="malo_consumption",
        translation_key="malo_consumption",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_entity_name=True,
    ),
    SensorEntityDescription(
        key="malo_production",
        translation_key="malo_production",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_entity_name=True,
    ),
)


class MetiundoReadingMetadataSensor(SensorEntity, MetiundoEntity):
    """Expose timestamp and quality metadata for the latest reading."""

    def __init__(
        self,
        coordinator: MetiundoDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the metadata sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> datetime | str | None:
        """Return the selected reading metadata."""
        reading = self.coordinator.data.latest_reading
        if self.entity_description.key == "last_reading_time":
            return reading.reading_time
        if self.entity_description.key == "reading_quality":
            return reading.received_status
        point = self.coordinator.data.metering_point
        return {
            "metering_point_address": point.address,
            "melo": point.melo,
            "malo_consumption": point.malo_consumption,
            "malo_production": point.malo_production,
        }.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return whether the metadata value exists."""
        return super().available and self.native_value is not None
