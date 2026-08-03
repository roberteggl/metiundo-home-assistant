"""Tests for Metiundo API response normalization."""

from datetime import UTC, datetime

import pytest

from custom_components.metiundo.api.models import MetiundoMeteringPoint, MetiundoReading


@pytest.mark.unit
def test_reading_converts_mwh_to_kwh_and_timestamp() -> None:
    """Energy registers are converted from mWh to kWh."""
    reading = MetiundoReading.from_api(
        {
            "readingTime": 1_663_344_900_000,
            "serverTime": 1_663_344_900_000,
            "energyOut": 578_216_900,
            "energyIn": 12_000_000,
            "receivedStatus": "W",
        },
    )

    assert reading.reading_time == datetime(2022, 9, 16, 16, 15, tzinfo=UTC)
    assert reading.energy_out_kwh == pytest.approx(578.2169)
    assert reading.energy_in_kwh == pytest.approx(12)


@pytest.mark.unit
def test_metering_point_parses_capabilities() -> None:
    """Metering-point metadata exposes supported energy fields."""
    point = MetiundoMeteringPoint.from_api(
        {
            "uuid": "point-1",
            "meterType": "electricity_iot",
            "name": "Home",
            "address": "69118 Heidelberg, Street 1",
            "melo": "DE0009565555550000000000000004879",
            "maloConsumption": "50173288123",
            "maloProduction": "50173288456",
            "availableFields": ["energyOut"],
        },
    )

    assert point.supports_energy
    assert point.available_fields == {"energyOut"}
    assert point.address == "69118 Heidelberg, Street 1"
    assert point.melo == "DE0009565555550000000000000004879"
    assert point.malo_consumption == "50173288123"
    assert point.malo_production == "50173288456"
