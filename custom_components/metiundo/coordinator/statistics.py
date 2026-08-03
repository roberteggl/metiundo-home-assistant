"""Import Metiundo batch readings into Home Assistant long-term statistics."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from itertools import pairwise
from typing import TYPE_CHECKING, Literal

from custom_components.metiundo.api.models import MetiundoMeteringPoint, MetiundoReading
from custom_components.metiundo.const import (
    CONF_ARBEITSPREIS_CT_PER_KWH,
    CONF_ENABLE_COST_METRICS,
    CONF_GRUNDPREIS_EUR_PER_MONTH,
    CONF_TARIFF_EFFECTIVE_FROM,
    CONF_TARIFFS,
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
class MetiundoTariff:
    """Current electricity tariff used for cost statistics."""

    arbeitspreis_eur_per_kwh: float
    grundpreis_eur_per_month: float
    effective_from: date


@dataclass(frozen=True, slots=True)
class _LastStatistic:
    """Latest imported statistic used as the next cumulative baseline."""

    start: datetime
    total: float


def _parse_tariff(value: Mapping[str, object]) -> MetiundoTariff | None:
    """Parse one stored tariff and normalize it to the first day of its month."""
    arbeitspreis = value.get(CONF_ARBEITSPREIS_CT_PER_KWH)
    grundpreis = value.get(CONF_GRUNDPREIS_EUR_PER_MONTH)
    effective_from = value.get(CONF_TARIFF_EFFECTIVE_FROM)
    if (
        isinstance(arbeitspreis, bool)
        or not isinstance(arbeitspreis, (int, float))
        or arbeitspreis < 0
        or isinstance(grundpreis, bool)
        or not isinstance(grundpreis, (int, float))
        or grundpreis < 0
    ):
        return None

    if isinstance(effective_from, date):
        effective_date = effective_from
    elif isinstance(effective_from, str):
        try:
            effective_date = date.fromisoformat(effective_from)
        except ValueError:
            return None
    else:
        return None

    return MetiundoTariff(
        arbeitspreis_eur_per_kwh=float(arbeitspreis) / 100,
        grundpreis_eur_per_month=float(grundpreis),
        effective_from=effective_date.replace(day=1),
    )


def get_configured_tariffs(entry: MetiundoConfigEntry) -> tuple[MetiundoTariff, ...]:
    """Return the ordered tariff schedule, if cost statistics are enabled."""
    if not entry.options.get(CONF_ENABLE_COST_METRICS, False):
        return ()

    configured_tariffs = entry.options.get(CONF_TARIFFS)
    if isinstance(configured_tariffs, list):
        tariff_values = configured_tariffs
    else:
        tariff_values = [entry.options]

    tariffs = tuple(
        sorted(
            (
                tariff
                for value in tariff_values
                if isinstance(value, Mapping) and (tariff := _parse_tariff(value)) is not None
            ),
            key=lambda tariff: tariff.effective_from,
        ),
    )
    if not tariffs:
        LOGGER.warning("Cost statistics are enabled but no valid Metiundo tariffs are configured")
    return tariffs


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

    tariffs = get_configured_tariffs(entry)
    if not tariffs:
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

    cost_statistics = build_hourly_cost_statistics(readings, tariffs, last_cost_statistic)
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
    tariffs: tuple[MetiundoTariff, ...],
    last_statistic: _LastStatistic | None = None,
) -> list[StatisticData]:
    """Build hourly import costs from cumulative meter readings and a tariff schedule."""
    ordered_readings = sorted(
        {reading.reading_time: reading for reading in readings if reading.reading_time is not None}.values(),
        key=lambda reading: reading.reading_time or datetime.min.replace(tzinfo=UTC),
    )
    buckets: dict[datetime, tuple[float, date]] = {}
    month_tariffs: dict[date, MetiundoTariff] = {}

    for previous, latest in pairwise(ordered_readings):
        if previous.reading_time is None or latest.reading_time is None:
            continue
        previous_value = previous.energy_out_kwh
        latest_value = latest.energy_out_kwh
        if previous_value is None or latest_value is None or latest_value < previous_value:
            continue

        previous_local = dt_util.as_local(previous.reading_time)
        month = previous_local.date().replace(day=1)
        tariff = max(
            (candidate for candidate in tariffs if candidate.effective_from <= month),
            key=lambda candidate: candidate.effective_from,
            default=None,
        )
        if tariff is None:
            continue

        bucket_start = dt_util.as_utc(previous.reading_time).replace(minute=0, second=0, microsecond=0)
        state, existing_month = buckets.get(bucket_start, (0.0, month))
        month_tariffs[month] = tariff
        buckets[bucket_start] = (
            state + (latest_value - previous_value) * tariff.arbeitspreis_eur_per_kwh,
            existing_month,
        )

    last_start = last_statistic.start if last_statistic else None
    running_total = last_statistic.total if last_statistic else 0.0
    applied_months: set[date] = set()
    if last_start is not None:
        last_local = dt_util.as_local(last_start)
        applied_months.add(last_local.date().replace(day=1))

    statistics: list[StatisticData] = []
    for start, (state, month) in sorted(buckets.items()):
        if last_start is not None and start <= last_start:
            continue
        if month not in applied_months:
            state += month_tariffs[month].grundpreis_eur_per_month
            applied_months.add(month)
        running_total += state
        statistics.append(StatisticData(start=start, state=state, sum=running_total))

    return statistics
