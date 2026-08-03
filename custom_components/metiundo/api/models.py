"""Typed models for responses from the Metiundo API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _number_or_none(value: Any) -> float | None:
    """Return a numeric API value, preserving missing optional fields."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"Expected a number, got {type(value).__name__}")
    return float(value)


def _timestamp_or_none(value: Any) -> datetime | None:
    """Convert an API millisecond timestamp to an aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"Expected a millisecond timestamp, got {type(value).__name__}")
    return datetime.fromtimestamp(value / 1000, tz=UTC)


@dataclass(frozen=True)
class MetiundoReading:
    """A raw electricity reading returned by the API."""

    reading_time: datetime | None
    server_time: datetime | None
    energy_out_mwh: float | None
    energy_in_mwh: float | None
    received_status: str | None

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> MetiundoReading:
        """Build a reading from an OpenAPI response object."""
        return cls(
            reading_time=_timestamp_or_none(payload.get("readingTime")),
            server_time=_timestamp_or_none(payload.get("serverTime")),
            energy_out_mwh=_number_or_none(payload.get("energyOut")),
            energy_in_mwh=_number_or_none(payload.get("energyIn")),
            received_status=payload.get("receivedStatus"),
        )

    @property
    def energy_out_kwh(self) -> float | None:
        """Return cumulative consumption in kWh."""
        if self.energy_out_mwh is None:
            return None
        return self.energy_out_mwh / 1_000_000

    @property
    def energy_in_kwh(self) -> float | None:
        """Return cumulative production in kWh."""
        if self.energy_in_mwh is None:
            return None
        return self.energy_in_mwh / 1_000_000


@dataclass(frozen=True)
class MetiundoMeteringPoint:
    """A metering point accessible to the authenticated account."""

    uuid: str
    meter_type: str
    name: str
    description: str | None
    address: str | None
    sensor_identifier: str | None
    available_fields: frozenset[str]
    last_reading: MetiundoReading | None
    melo: str | None = None
    malo_consumption: str | None = None
    malo_production: str | None = None

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> MetiundoMeteringPoint:
        """Build a metering point from an OpenAPI response object."""
        uuid = payload.get("uuid")
        if not isinstance(uuid, str) or not uuid:
            raise ValueError("Metering point response has no valid uuid")

        available_fields = payload.get("availableFields", [])
        if not isinstance(available_fields, list) or not all(isinstance(field, str) for field in available_fields):
            raise ValueError("Metering point response has invalid availableFields")

        last_reading = payload.get("lastReading")
        if last_reading is not None and not isinstance(last_reading, Mapping):
            raise ValueError("Metering point response has an invalid lastReading")

        return cls(
            uuid=uuid,
            meter_type=str(payload.get("meterType", "")),
            name=str(payload.get("name") or uuid),
            description=payload.get("description"),
            address=payload.get("address"),
            sensor_identifier=payload.get("sensorIdentifier"),
            available_fields=frozenset(available_fields),
            last_reading=MetiundoReading.from_api(last_reading) if last_reading else None,
            melo=payload.get("melo"),
            malo_consumption=payload.get("maloConsumption"),
            malo_production=payload.get("maloProduction"),
        )

    @property
    def supports_energy(self) -> bool:
        """Return whether this point can provide at least one energy register."""
        return bool({"energyOut", "energyIn"} & self.available_fields)
