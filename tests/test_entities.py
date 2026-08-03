"""Integration tests for Metiundo entities."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.metiundo.api import MetiundoMeteringPoint, MetiundoReading
from custom_components.metiundo.const import CONF_ENABLE_EXPORT_METRICS, CONF_METERING_POINT_UUID, DOMAIN
from homeassistant import loader
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("export_metrics_enabled", [True, False])
async def test_setup_creates_energy_entities(hass: HomeAssistant, export_metrics_enabled: bool) -> None:
    """A configured electricity point creates import and export sensors."""
    loader.async_setup(hass)
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)
    await loader.async_get_custom_components(hass)

    point = MetiundoMeteringPoint(
        uuid="point-1",
        meter_type="electricity",
        name="Home",
        description=None,
        address="69118 Heidelberg, Street 1",
        sensor_identifier="meter-1",
        available_fields=frozenset({"energyOut", "energyIn"}),
        last_reading=None,
        melo="DE0009565555550000000000000004879",
        malo_consumption="50173288123",
        malo_production="50173288456",
    )
    reading = MetiundoReading(
        reading_time=datetime(2026, 8, 3, tzinfo=UTC),
        server_time=datetime(2026, 8, 3, tzinfo=UTC),
        energy_out_mwh=1_000_000,
        energy_in_mwh=2_000_000,
        received_status="W",
    )
    previous_reading = MetiundoReading(
        reading_time=datetime(2026, 8, 2, 23, 0, tzinfo=UTC),
        server_time=datetime(2026, 8, 2, 23, 0, tzinfo=UTC),
        energy_out_mwh=500_000,
        energy_in_mwh=1_000_000,
        received_status="W",
    )
    fake_client = MagicMock()
    fake_client.async_get_metering_point = AsyncMock(return_value=point)
    fake_client.async_get_data = AsyncMock(return_value=reading)
    fake_client.async_get_readings = AsyncMock(return_value=[previous_reading, reading])
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="user@example.com",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret",
            CONF_METERING_POINT_UUID: "point-1",
        },
        options={CONF_ENABLE_EXPORT_METRICS: export_metrics_enabled},
    )
    entry.add_to_hass(hass)

    with patch("custom_components.metiundo.MetiundoApiClient", return_value=fake_client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.home_grid_import_energy").state == "1.0"
    if export_metrics_enabled:
        assert hass.states.get("sensor.home_grid_export_energy").state == "2.0"
    else:
        assert hass.states.get("sensor.home_grid_export_energy") is None
    assert hass.states.get("sensor.home_reading_quality").state == "W"
    assert hass.states.get("sensor.home_last_reading_time") is not None
    assert hass.states.get("binary_sensor.home_api_connection").state == "on"

    entity_registry = er.async_get(hass)
    for entity_id in (
        "sensor.home_metering_point_address",
        "sensor.home_melo_id",
        "sensor.home_malo_id_consumption",
        "sensor.home_malo_id_production",
    ):
        assert entity_registry.async_get(entity_id).disabled
