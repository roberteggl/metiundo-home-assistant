"""Import Metiundo batch readings into Home Assistant long-term statistics."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from itertools import pairwise
from typing import TYPE_CHECKING, Literal

from custom_components.metiundo.api.models import MetiundoMeteringPoint, MetiundoReading
from custom_components.metiundo.const import DOMAIN, LOGGER
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import EnergyConverter

if TYPE_CHECKING:
    from custom_components.metiundo.data import MetiundoConfigEntry

EnergyRegister = Literal["energy_out_kwh", "energy_in_kwh"]


def async_import_reading_statistics(
    hass: HomeAssistant,
    entry: MetiundoConfigEntry,
    metering_point: MetiundoMeteringPoint,
    readings: Iterable[MetiundoReading],
) -> tuple[int, bool]:
    """Import daily readings as hourly external statistics."""
    if "recorder" not in hass.config.components:
        return 0, True

    entry_id = entry.entry_id.replace("-", "_").lower()
    registers: tuple[tuple[EnergyRegister, str, str], ...] = (
        ("energy_out_kwh", "grid_import_energy", "Grid import energy"),
        ("energy_in_kwh", "grid_export_energy", "Grid export energy"),
    )
    if not entry.options.get("enable_export_metrics", True):
        registers = registers[:1]

    imported_count = 0
    import_succeeded = True
    for register, statistic_suffix, statistic_name in registers:
        statistics = build_hourly_statistics(readings, register)
        if not statistics:
            continue
        metadata = StatisticMetaData(
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:{entry_id}_{statistic_suffix}",
            name=f"{metering_point.name} {statistic_name}",
            unit_class=EnergyConverter.UNIT_CLASS,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
        )
        try:
            async_add_external_statistics(hass, metadata, statistics)
            imported_count += len(statistics)
        except HomeAssistantError as exception:
            import_succeeded = False
            LOGGER.warning("Unable to import Metiundo statistics: %s", exception)

    return imported_count, import_succeeded


def build_hourly_statistics(
    readings: Iterable[MetiundoReading],
    register: EnergyRegister,
) -> list[StatisticData]:
    """Aggregate cumulative 15-minute readings into hourly statistics."""
    ordered_readings = sorted(
        {reading.reading_time: reading for reading in readings if reading.reading_time is not None}.values(),
        key=lambda reading: reading.reading_time or datetime.min,
    )
    buckets: dict[datetime, list[float]] = defaultdict(lambda: [0.0, 0.0])

    for previous, latest in pairwise(ordered_readings):
        if previous.reading_time is None or latest.reading_time is None:
            continue
        previous_value = getattr(previous, register)
        latest_value = getattr(latest, register)
        if previous_value is None or latest_value is None or latest_value < previous_value:
            continue

        bucket_start = dt_util.as_utc(previous.reading_time).replace(minute=0, second=0, microsecond=0)
        bucket = buckets[bucket_start]
        bucket[0] += latest_value - previous_value
        bucket[1] = latest_value

    return [StatisticData(start=start, state=values[0], sum=values[1]) for start, values in sorted(buckets.items())]
