"""Energy sensors for the selected Metiundo metering point."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.metiundo.entity import MetiundoEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfEnergy

if TYPE_CHECKING:
    from custom_components.metiundo.coordinator import MetiundoDataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="grid_import_energy",
        translation_key="grid_import_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        has_entity_name=True,
    ),
    SensorEntityDescription(
        key="grid_export_energy",
        translation_key="grid_export_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        has_entity_name=True,
    ),
)


class MetiundoEnergySensor(SensorEntity, MetiundoEntity):
    """Expose one cumulative energy register as a Home Assistant sensor."""

    def __init__(
        self,
        coordinator: MetiundoDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> float | None:
        """Return the latest cumulative energy value in kWh."""
        reading = self.coordinator.data.latest_reading
        if self.entity_description.key == "grid_import_energy":
            return reading.energy_out_kwh
        return reading.energy_in_kwh

    @property
    def available(self) -> bool:
        """Return whether the selected register is available."""
        if not super().available:
            return False
        field = "energyOut" if self.entity_description.key == "grid_import_energy" else "energyIn"
        return field in self.coordinator.data.metering_point.available_fields and self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return reading metadata useful for troubleshooting."""
        reading = self.coordinator.data.latest_reading
        return {
            "metering_point_uuid": self.coordinator.data.metering_point.uuid,
            "reading_time": reading.reading_time.isoformat() if reading.reading_time else None,
            "received_status": reading.received_status,
        }
