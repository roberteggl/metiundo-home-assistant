"""Data update coordinator for the selected Metiundo metering point."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from typing import TYPE_CHECKING, NoReturn

from custom_components.metiundo.api import (
    MetiundoApiClientAuthenticationError,
    MetiundoApiClientError,
    MetiundoApiClientRateLimitError,
    MetiundoMeteringPoint,
    MetiundoReading,
)
from custom_components.metiundo.const import (
    CONF_HISTORY_START_DATE,
    CONF_IMPORT_HISTORICAL_DATA,
    CONF_METERING_POINT_UUID,
    DOMAIN,
    INITIAL_HISTORY_CHUNK_DAYS,
    ISSUE_HISTORICAL_IMPORT_FAILED,
    ISSUE_NO_RECENT_DATA,
    READINGS_LOOKBACK_HOURS,
)
from custom_components.metiundo.coordinator.statistics import async_import_reading_statistics
from custom_components.metiundo.data import MetiundoCoordinatorData
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from custom_components.metiundo.data import MetiundoConfigEntry


def _raise_update_failed(message: str) -> NoReturn:
    """Raise an update failure from a historical import operation."""
    raise UpdateFailed(message)


class MetiundoDataUpdateCoordinator(DataUpdateCoordinator[MetiundoCoordinatorData]):
    """Fetch and normalize data shared by all Metiundo entities."""

    config_entry: MetiundoConfigEntry
    _metering_point: MetiundoMeteringPoint

    last_fetch_range_start: datetime | None = None
    last_fetch_range_end: datetime | None = None
    last_fetch_reading_count = 0
    last_statistics_count = 0
    last_statistics_import_succeeded: bool | None = None
    last_historical_import_start_date: str | None = None
    last_historical_import_completed_at: datetime | None = None
    last_historical_import_error: str | None = None
    _historical_import_lock: asyncio.Lock

    async def _async_setup(self) -> None:
        """Load the selected metering point metadata once."""
        self._historical_import_lock = asyncio.Lock()
        identifier = self.config_entry.data.get(CONF_METERING_POINT_UUID)
        if not isinstance(identifier, str) or not identifier:
            raise UpdateFailed("The selected Metiundo metering point is not configured")
        try:
            self._metering_point = await self.config_entry.runtime_data.client.async_get_metering_point(identifier)
        except MetiundoApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(
                translation_domain="metiundo",
                translation_key="authentication_failed",
            ) from exception
        except MetiundoApiClientError as exception:
            raise UpdateFailed(
                f"Failed to initialize the selected metering point: {exception}",
            ) from exception

    async def _async_update_data(self) -> MetiundoCoordinatorData:
        """Fetch the daily batch and return normalized coordinator data."""
        now = datetime.now(UTC)
        try:
            readings = await self._async_fetch_readings(now)
        except MetiundoApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(
                translation_domain="metiundo",
                translation_key="authentication_failed",
            ) from exception
        except MetiundoApiClientRateLimitError as exception:
            self._mark_historical_import_failed(str(exception))
            raise UpdateFailed(
                f"Metiundo API rate limit exceeded: {exception}",
                retry_after=exception.retry_after or 60,
            ) from exception
        except MetiundoApiClientError as exception:
            self._mark_historical_import_failed(str(exception))
            raise UpdateFailed(
                f"Failed to update data from the server: {exception}",
            ) from exception

        readings = [reading for reading in readings if reading.reading_time is not None]
        self.last_fetch_reading_count = len(readings)
        if not readings:
            if self._historical_import_requested:
                self._mark_historical_import_failed("No readings were returned for the selected date range")
            else:
                self._create_issue(
                    ISSUE_NO_RECENT_DATA,
                    "no_recent_data",
                    "No readings were returned by the API",
                )
            raise UpdateFailed("The selected metering point has no readings in the requested range")

        reading = max(
            readings,
            key=lambda item: item.reading_time or datetime.min.replace(tzinfo=UTC),
        )
        statistics_count, statistics_import_succeeded = async_import_reading_statistics(
            self.hass,
            self.config_entry,
            self._metering_point,
            readings,
        )
        self.last_statistics_count = statistics_count
        self.last_statistics_import_succeeded = statistics_import_succeeded
        if not statistics_import_succeeded:
            self._mark_historical_import_failed("Home Assistant rejected one or more statistics batches")
        elif self._historical_import_requested:
            self.last_historical_import_completed_at = datetime.now(UTC)
            self.last_historical_import_error = None
            self._delete_issue(ISSUE_HISTORICAL_IMPORT_FAILED)
            options = dict(self.config_entry.options)
            options.pop(CONF_IMPORT_HISTORICAL_DATA, None)
            options.pop(CONF_HISTORY_START_DATE, None)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=options,
            )
        if reading.reading_time and reading.reading_time < now - timedelta(hours=READINGS_LOOKBACK_HOURS):
            self._create_issue(
                ISSUE_NO_RECENT_DATA,
                "no_recent_data",
                f"The latest reading is from {reading.reading_time.isoformat()}",
            )
        else:
            self._delete_issue(ISSUE_NO_RECENT_DATA)
        return MetiundoCoordinatorData(
            metering_point=self._metering_point,
            latest_reading=reading,
        )

    async def async_import_historical_data(
        self,
        start_date: date,
        end_date: date | None = None,
    ) -> dict[str, int | str | None]:
        """Import a requested historical date range into long-term statistics."""
        now = datetime.now(UTC)
        start = datetime.combine(start_date, time.min, tzinfo=UTC)
        if start > now - timedelta(hours=READINGS_LOOKBACK_HOURS):
            raise ValueError("The historical import must start at least 48 hours ago")

        end = now
        if end_date is not None:
            if end_date < start_date:
                raise ValueError("The historical import end date must not precede the start date")
            requested_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
            end = min(now, requested_end)
        if start >= end:
            raise ValueError("The historical import date range is empty")

        async with self._historical_import_lock:
            self.last_historical_import_start_date = start_date.isoformat()
            self.last_fetch_range_start = start
            self.last_fetch_range_end = end
            try:
                readings, chunk_count = await self._async_fetch_range(start, end)
                readings = [reading for reading in readings if reading.reading_time is not None]
                self.last_fetch_reading_count = len(readings)
                if not readings:
                    _raise_update_failed("No readings were returned for the requested date range")

                statistics_count, statistics_import_succeeded = async_import_reading_statistics(
                    self.hass,
                    self.config_entry,
                    self._metering_point,
                    readings,
                )
                self.last_statistics_count = statistics_count
                self.last_statistics_import_succeeded = statistics_import_succeeded
                if not statistics_import_succeeded:
                    _raise_update_failed("Home Assistant rejected one or more statistics batches")

                latest_reading = max(readings, key=lambda item: item.reading_time or datetime.min.replace(tzinfo=UTC))
                self.last_historical_import_completed_at = datetime.now(UTC)
                self.last_historical_import_error = None
                self._delete_issue(ISSUE_HISTORICAL_IMPORT_FAILED)
                return {
                    "start_date": start_date.isoformat(),
                    "end_date": (min(end_date, now.date()) if end_date is not None else end.date()).isoformat(),
                    "chunk_count": chunk_count,
                    "reading_count": len(readings),
                    "statistics_count": statistics_count,
                    "latest_reading": latest_reading.reading_time.isoformat() if latest_reading.reading_time else None,
                }
            except (MetiundoApiClientError, UpdateFailed) as exception:
                self.last_historical_import_error = str(exception)
                self._create_issue(ISSUE_HISTORICAL_IMPORT_FAILED, "historical_import_failed", str(exception))
                raise

    async def _async_fetch_readings(self, now: datetime) -> list[MetiundoReading]:
        """Fetch either the normal lookback or the one-time initial history."""
        end = now
        history_start_date = self.config_entry.options.get(CONF_HISTORY_START_DATE)
        if not self.config_entry.options.get(CONF_IMPORT_HISTORICAL_DATA, False):
            self.last_fetch_range_start = now - timedelta(hours=READINGS_LOOKBACK_HOURS)
            self.last_fetch_range_end = now
            readings, _ = await self._async_fetch_range(self.last_fetch_range_start, end)
            return readings
        if not isinstance(history_start_date, str):
            raise MetiundoApiClientError("The historical import start date is not configured")

        try:
            start = datetime.combine(date.fromisoformat(history_start_date), time.min, tzinfo=UTC)
        except ValueError as exception:
            raise MetiundoApiClientError("The historical import start date is invalid") from exception
        self.last_historical_import_start_date = history_start_date
        self.last_fetch_range_start = start
        self.last_fetch_range_end = now
        readings, _ = await self._async_fetch_range(start, end)
        return readings

    async def _async_fetch_range(self, start: datetime, end: datetime) -> tuple[list[MetiundoReading], int]:
        """Fetch a date range in bounded API requests."""
        identifier = self.config_entry.data[CONF_METERING_POINT_UUID]
        readings: list[MetiundoReading] = []
        chunk_count = 0
        while end > start:
            chunk_start = max(start, end - timedelta(days=INITIAL_HISTORY_CHUNK_DAYS))
            readings.extend(
                await self.config_entry.runtime_data.client.async_get_readings(
                    identifier,
                    int(chunk_start.timestamp() * 1000),
                    int(end.timestamp() * 1000),
                ),
            )
            chunk_count += 1
            end = chunk_start
        return readings, chunk_count

    @property
    def _historical_import_requested(self) -> bool:
        """Return whether the one-time historical import is still pending."""
        return bool(self.config_entry.options.get(CONF_IMPORT_HISTORICAL_DATA, False))

    def _issue_id(self, issue: str) -> str:
        """Return an issue ID unique to this config entry."""
        return f"{issue}_{self.config_entry.entry_id}"

    def _create_issue(self, issue: str, translation_key: str, error: str) -> None:
        """Create a persistent, non-fixable issue for this config entry."""
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._issue_id(issue),
            data={"error": error},
            is_fixable=False,
            is_persistent=True,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders={"error": error},
        )

    def _delete_issue(self, issue: str) -> None:
        """Delete an issue after the corresponding condition is resolved."""
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id(issue))

    def _mark_historical_import_failed(self, error: str) -> None:
        """Record and expose a failed historical import when one is pending."""
        if not self._historical_import_requested:
            return
        self.last_historical_import_error = error
        self._create_issue(ISSUE_HISTORICAL_IMPORT_FAILED, "historical_import_failed", error)
