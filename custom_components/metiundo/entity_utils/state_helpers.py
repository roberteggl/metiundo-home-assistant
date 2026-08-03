"""State helper utilities for metiundo."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def format_state_value(value: Any, unit: str | None = None) -> str:
    """
    Format a state value for display.

    Args:
        value: The value to format
        unit: Optional unit to append

    Returns:
        A formatted string representation of the value

    Example:
        >>> format_state_value(25.5, "°C")
        '25.5 °C'
        >>> format_state_value(True)
        'on'
    """
    if isinstance(value, bool):
        return "on" if value else "off"

    if isinstance(value, (int, float)):
        formatted = f"{value:.2f}" if isinstance(value, float) else str(value)
        return f"{formatted} {unit}" if unit else formatted

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value) if value is not None else "unknown"


def parse_state_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """
    Parse and extract state attributes from raw data.

    Args:
        data: Raw data from the API

    Returns:
        A dictionary of state attributes

    Example:
        >>> parse_state_attributes({"readings": [{"energyOut": 12.5}]})
        {'reading_count': 1, 'has_readings': True}
    """
    attributes = {}

    # Extract readings if present
    readings = data.get("readings", [])
    if isinstance(readings, list):
        attributes["reading_count"] = len(readings)

    # Extract energy values if present
    if "energyOut" in data:
        attributes["grid_import_kwh"] = data["energyOut"]

    if "energyIn" in data:
        attributes["grid_export_kwh"] = data["energyIn"]

    # Add computed attributes
    if readings:
        attributes["has_readings"] = bool(readings)

    return attributes


def merge_state_attributes(
    base_attrs: dict[str, Any],
    new_attrs: dict[str, Any],
    preserve_keys: list[str] | None = None,
) -> dict[str, Any]:
    """
    Merge new state attributes with existing ones.

    Args:
        base_attrs: Base attributes
        new_attrs: New attributes to merge
        preserve_keys: Optional list of keys to preserve from base_attrs

    Returns:
        Merged attributes dictionary

    Example:
        >>> base = {"key1": "value1", "key2": "value2"}
        >>> new = {"key2": "new_value2", "key3": "value3"}
        >>> merge_state_attributes(base, new, preserve_keys=["key1"])
        {'key1': 'value1', 'key2': 'new_value2', 'key3': 'value3'}
    """
    merged = dict(base_attrs)

    # Update with new attributes
    merged.update(new_attrs)

    # Restore preserved keys if specified
    if preserve_keys:
        for key in preserve_keys:
            if key in base_attrs:
                merged[key] = base_attrs[key]

    return merged


def calculate_derived_state(data: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate derived state values from raw data.

    Args:
        data: Raw data from the API

    Returns:
        A dictionary of derived state values

    Example:
        >>> calculate_derived_state({"readings": [{"energyOut": 12.5}]})
        {'has_data': True, 'data_quality': 'good'}
    """
    derived = {}

    # Determine if meter readings are available
    derived["has_data"] = bool(data.get("readings"))

    # Assess data quality
    if data.get("readings"):
        derived["data_quality"] = "good"
    elif data.get("energyOut") is not None or data.get("energyIn") is not None:
        derived["data_quality"] = "partial"
    else:
        derived["data_quality"] = "poor"

    return derived
