"""Tests for Metiundo external statistics aggregation."""

from datetime import UTC, datetime

import pytest

from custom_components.metiundo.api.models import MetiundoReading
from custom_components.metiundo.coordinator.statistics import build_hourly_statistics


@pytest.mark.unit
def test_build_hourly_statistics_aggregates_15_minute_readings() -> None:
    """Four quarter-hour deltas become one hourly statistic."""
    readings = [
        MetiundoReading(
            reading_time=datetime(2026, 8, 3, 0, minute, tzinfo=UTC),
            server_time=None,
            energy_out_mwh=(minute // 15) * 250_000,
            energy_in_mwh=None,
            received_status="W",
        )
        for minute in (0, 15, 30, 45, 0)
    ]
    readings[-1] = MetiundoReading(
        reading_time=datetime(2026, 8, 3, 1, tzinfo=UTC),
        server_time=None,
        energy_out_mwh=1_000_000,
        energy_in_mwh=None,
        received_status="W",
    )

    statistics = build_hourly_statistics(readings, "energy_out_kwh")

    assert len(statistics) == 1
    assert statistics[0]["state"] == pytest.approx(1)
    assert statistics[0]["sum"] == pytest.approx(1)
