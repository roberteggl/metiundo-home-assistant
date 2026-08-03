"""
Base entity class for metiundo.

This module provides the base entity class that all integration entities inherit from.
It handles common functionality like device info, unique IDs, and coordinator integration.

For more information on entities:
https://developers.home-assistant.io/docs/core/entity
https://developers.home-assistant.io/docs/core/entity/index/#common-properties
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.metiundo.const import ATTRIBUTION, MANUFACTURER, PORTAL_URL
from custom_components.metiundo.coordinator import MetiundoDataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class MetiundoEntity(CoordinatorEntity[MetiundoDataUpdateCoordinator]):
    """
    Base entity class for metiundo.

    All entities in this integration inherit from this class, which provides:
    - Automatic coordinator updates
    - Device info management
    - Unique ID generation
    - Attribution and naming conventions

    For more information:
    https://developers.home-assistant.io/docs/core/entity
    https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MetiundoDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """
        Initialize the base entity.

        Args:
            coordinator: The data update coordinator for this entity.
            entity_description: The entity description defining characteristics.

        """
        super().__init__(coordinator)
        self.entity_description = entity_description
        # Include entity description key in unique_id to support multiple entities
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        metering_point = coordinator.data.metering_point if coordinator.data else None
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
            name=metering_point.name if metering_point else coordinator.config_entry.title,
            manufacturer=MANUFACTURER,
            model=metering_point.meter_type if metering_point else "Smart Meter",
            serial_number=metering_point.sensor_identifier if metering_point else None,
            configuration_url=PORTAL_URL,
        )
