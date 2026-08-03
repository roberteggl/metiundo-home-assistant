"""Connectivity binary sensor for metiundo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.metiundo.const import API_BASE_URL
from custom_components.metiundo.entity import MetiundoEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.metiundo.coordinator import MetiundoDataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="api_connectivity",
        translation_key="api_connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:api",
        has_entity_name=True,
    ),
)


class MetiundoConnectivitySensor(BinarySensorEntity, MetiundoEntity):
    """Connectivity sensor for metiundo."""

    def __init__(
        self,
        coordinator: MetiundoDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if the API connection is established."""
        # Connection is considered established if coordinator has valid data
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return additional state attributes."""
        attributes: dict[str, str | None] = {
            "update_interval": str(self.coordinator.update_interval),
            "api_endpoint": API_BASE_URL,
        }
        if self.coordinator.data:
            point = self.coordinator.data.metering_point
            reading = self.coordinator.data.latest_reading
            attributes.update(
                {
                    "metering_point_uuid": point.uuid,
                    "reading_time": reading.reading_time.isoformat() if reading.reading_time else None,
                    "received_status": reading.received_status,
                },
            )
        return attributes
