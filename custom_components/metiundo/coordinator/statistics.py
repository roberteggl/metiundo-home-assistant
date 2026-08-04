"""Import Metiundo batch readings into Home Assistant long-term statistics."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import TYPE_CHECKING, Literal

from custom_components.metiundo.api.models import MetiundoMeteringPoint, MetiundoReading
from custom_components.metiundo.const import (
    CONF_ARBEITSPREIS_CT_PER_KWH,
    CONF_ENABLE_COST_METRICS,
    DOMAIN,
    LOGGER,
    STATISTIC_GRID_IMPORT_COST,
)
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics, get_last_statistics
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import EnergyConverter

if TYPE_CHECKING:
    from custom_components.metiundo.data import MetiundoConfigEntry

EnergyRegister = Literal["energy_out_kwh", "energy_in_kwh"]


@dataclass(frozen=True, slots=True)
class _LastStatistic:
    """Latest imported statistic used as the next cumulative baseline."""

    start: datetime
    total: float


def get_configured_working_price(entry: MetiundoConfigEntry) -> float | None:
    """Return the single configured working price in cents per kWh."""
    if not entry.options.get(CONF_ENABLE_COST_METRICS, False):
        return None

    working_price = entry.options.get(CONF_ARBEITSPREIS_CT_PER_KWH)
    if isinstance(working_price, bool) or not isinstance(working_price, (int, float)) or working_price < 0:
        LOGGER.warning("Cost statistics are enabled but no valid working price is configured")
        return None
    return float(working_price)


async def async_import_reading_statistics(
    hass: HomeAssistant,
    entry: MetiundoConfigEntry,
    metering_point: MetiundoMeteringPoint,
    readings: Iterable[MetiundoReading],
    rebuild_statistics: bool = False,
) -> tuple[int, bool]:
    """Import daily readings as hourly external statistics."""
    if "recorder" not in hass.config.components:
        return 0, True

    readings = tuple(readings)
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
        statistic_id = f"{DOMAIN}:{entry_id}_{statistic_suffix}"
        if rebuild_statistics:
            last_statistic = None
        else:
            try:
                last_statistic = await _async_get_last_statistic(hass, statistic_id)
            except HomeAssistantError as exception:
                import_succeeded = False
                LOGGER.warning("Unable to read the previous Metiundo statistic: %s", exception)
                continue

        statistics = build_hourly_statistics(readings, register, last_statistic)
        if not statistics:
            continue
        metadata = StatisticMetaData(
            source=DOMAIN,
            statistic_id=statistic_id,
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

    working_price = get_configured_working_price(entry)
    if working_price is None:
        return imported_count, import_succeeded

    cost_statistic_id = f"{DOMAIN}:{entry_id}_{STATISTIC_GRID_IMPORT_COST}"
    if rebuild_statistics:
        last_cost_statistic = None
    else:
        try:
            last_cost_statistic = await _async_get_last_statistic(hass, cost_statistic_id)
        except HomeAssistantError as exception:
            LOGGER.warning("Unable to read the previous Metiundo cost statistic: %s", exception)
            return imported_count, False

    cost_statistics = build_hourly_cost_statistics(readings, working_price, last_cost_statistic)
    if not cost_statistics:
        return imported_count, import_succeeded

    cost_metadata = StatisticMetaData(
        source=DOMAIN,
        statistic_id=cost_statistic_id,
        name=f"{metering_point.name} Grid import cost",
        unit_class=None,
        unit_of_measurement=None,
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
    )
    try:
        async_add_external_statistics(hass, cost_metadata, cost_statistics)
        imported_count += len(cost_statistics)
    except HomeAssistantError as exception:
        import_succeeded = False
        LOGGER.warning("Unable to import Metiundo cost statistics: %s", exception)

    return imported_count, import_succeeded


async def _async_get_last_statistic(
    hass: HomeAssistant,
    statistic_id: str,
) -> _LastStatistic | None:
    """Read the latest external statistic without blocking the event loop."""
    latest_statistics = await get_instance(hass).async_add_executor_job(
        get_last_statistics,
        hass,
        1,
        statistic_id,
        False,
        {"sum"},
    )
    rows = latest_statistics.get(statistic_id)
    if not rows:
        return None
    row = rows[0]
    start = row.get("start")
    total = row.get("sum")
    if not isinstance(start, (int, float)) or not isinstance(total, (int, float)):
        return None
    return _LastStatistic(
        start=datetime.fromtimestamp(start, tz=UTC),
        total=float(total),
    )


def build_hourly_statistics(
    readings: Iterable[MetiundoReading],
    register: EnergyRegister,
    last_statistic: _LastStatistic | None = None,
) -> list[StatisticData]:
    """Aggregate cumulative 15-minute readings into hourly statistics."""
    ordered_readings = sorted(
        {reading.reading_time: reading for reading in readings if reading.reading_time is not None}.values(),
        key=lambda reading: reading.reading_time or datetime.min,
    )
    buckets: dict[datetime, float] = defaultdict(float)

    for previous, latest in pairwise(ordered_readings):
        if previous.reading_time is None or latest.reading_time is None:
            continue
        previous_value = getattr(previous, register)
        latest_value = getattr(latest, register)
        if previous_value is None or latest_value is None or latest_value < previous_value:
            continue

        bucket_start = dt_util.as_utc(previous.reading_time).replace(minute=0, second=0, microsecond=0)
        buckets[bucket_start] += latest_value - previous_value

    last_start = last_statistic.start if last_statistic else None
    running_total = last_statistic.total if last_statistic else 0.0
    statistics: list[StatisticData] = []
    for start, state in sorted(buckets.items()):
        if last_start is not None and start <= last_start:
            continue
        running_total += state
        statistics.append(StatisticData(start=start, state=state, sum=running_total))
    return statistics


def build_hourly_cost_statistics(
    readings: Iterable[MetiundoReading],
    working_price_ct_per_kwh: float,
    last_statistic: _LastStatistic | None = None,
) -> list[StatisticData]:
    """Build hourly import costs using one working price for every reading."""
    ordered_readings = sorted(
        {reading.reading_time: reading for reading in readings if reading.reading_time is not None}.values(),
        key=lambda reading: reading.reading_time or datetime.min.replace(tzinfo=UTC),
    )
    buckets: dict[datetime, float] = defaultdict(float)
    working_price_eur_per_kwh = working_price_ct_per_kwh / 100

    for previous, latest in pairwise(ordered_readings):
        if previous.reading_time is None or latest.reading_time is None:
            continue
        previous_value = previous.energy_out_kwh
        latest_value = latest.energy_out_kwh
        if previous_value is None or latest_value is None or latest_value < previous_value:
            continue

        bucket_start = dt_util.as_utc(previous.reading_time).replace(minute=0, second=0, microsecond=0)
        buckets[bucket_start] += (latest_value - previous_value) * working_price_eur_per_kwh

    last_start = last_statistic.start if last_statistic else None
    running_total = last_statistic.total if last_statistic else 0.0
    statistics: list[StatisticData] = []
    for start, state in sorted(buckets.items()):
        if last_start is not None and start <= last_start:
            continue
        running_total += state
        statistics.append(StatisticData(start=start, state=state, sum=running_total))

    return statistics
