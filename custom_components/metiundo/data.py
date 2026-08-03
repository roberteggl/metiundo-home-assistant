"""
Custom types for metiundo.

This module defines the runtime data structure attached to each config entry.
Access pattern: entry.runtime_data.client / entry.runtime_data.coordinator

The MetiundoConfigEntry type alias is used throughout the integration
for type-safe access to the config entry's runtime data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .api.models import MetiundoMeteringPoint, MetiundoReading

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import MetiundoApiClient
    from .coordinator import MetiundoDataUpdateCoordinator


type MetiundoConfigEntry = ConfigEntry[MetiundoData]


@dataclass
class MetiundoData:
    """Runtime data for metiundo config entries.

    Stored as entry.runtime_data after successful setup.
    Provides typed access to the API client and coordinator instances.
    """

    client: MetiundoApiClient
    coordinator: MetiundoDataUpdateCoordinator
    integration: Integration


@dataclass(frozen=True)
class MetiundoCoordinatorData:
    """Normalized data shared by all entities for one metering point."""

    metering_point: MetiundoMeteringPoint
    latest_reading: MetiundoReading
