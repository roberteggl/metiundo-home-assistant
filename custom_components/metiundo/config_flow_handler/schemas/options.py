"""
Options flow schemas.

Schemas for the options flow that allows users to modify settings
after initial configuration.

When adding many options, consider grouping them:
- basic_options.py: Common settings (update interval, debug mode)
- advanced_options.py: Advanced settings
- device_options.py: Device-specific settings
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import voluptuous as vol

from custom_components.metiundo.const import (
    CONF_ARBEITSPREIS_CT_PER_KWH,
    CONF_ENABLE_COST_METRICS,
    CONF_ENABLE_EXPORT_METRICS,
    CONF_GRUNDPREIS_EUR_PER_MONTH,
    CONF_TARIFF_EFFECTIVE_FROM,
    CONF_TARIFFS,
    DEFAULT_ARBEITSPREIS_CT_PER_KWH,
    DEFAULT_ENABLE_COST_METRICS,
    DEFAULT_ENABLE_DEBUGGING,
    DEFAULT_ENABLE_EXPORT_METRICS,
    DEFAULT_GRUNDPREIS_EUR_PER_MONTH,
    DEFAULT_UPDATE_INTERVAL_HOURS,
)
from homeassistant.helpers import selector


def _tariff_defaults(defaults: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the latest configured tariff for the options form."""
    configured_tariffs = defaults.get(CONF_TARIFFS)
    if isinstance(configured_tariffs, list):
        tariffs = [tariff for tariff in configured_tariffs if isinstance(tariff, Mapping)]
        if tariffs:
            return max(tariffs, key=lambda tariff: str(tariff.get(CONF_TARIFF_EFFECTIVE_FROM, "")))
    return defaults


def _effective_date_default(defaults: Mapping[str, Any]) -> date:
    """Return the first day of the latest configured tariff month."""
    configured_date = _tariff_defaults(defaults).get(CONF_TARIFF_EFFECTIVE_FROM)
    if isinstance(configured_date, date):
        return configured_date.replace(day=1)
    if isinstance(configured_date, str):
        try:
            return date.fromisoformat(configured_date).replace(day=1)
        except ValueError:
            pass
    return date.today().replace(day=1)


def get_options_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """
    Get schema for options flow.

    Args:
        defaults: Optional dictionary of current option values.

    Returns:
        Voluptuous schema for options configuration.

    """
    defaults = defaults or {}
    tariff_defaults = _tariff_defaults(defaults)
    return vol.Schema(
        {
            vol.Optional(
                "update_interval_hours",
                default=defaults.get("update_interval_hours", DEFAULT_UPDATE_INTERVAL_HOURS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.25,
                    max=24,
                    step=0.25,
                    unit_of_measurement="h",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                "enable_debugging",
                default=defaults.get("enable_debugging", DEFAULT_ENABLE_DEBUGGING),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_EXPORT_METRICS,
                default=defaults.get(CONF_ENABLE_EXPORT_METRICS, DEFAULT_ENABLE_EXPORT_METRICS),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_COST_METRICS,
                default=defaults.get(CONF_ENABLE_COST_METRICS, DEFAULT_ENABLE_COST_METRICS),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ARBEITSPREIS_CT_PER_KWH,
                default=tariff_defaults.get(CONF_ARBEITSPREIS_CT_PER_KWH, DEFAULT_ARBEITSPREIS_CT_PER_KWH),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=0.01,
                    unit_of_measurement="ct/kWh",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_GRUNDPREIS_EUR_PER_MONTH,
                default=tariff_defaults.get(CONF_GRUNDPREIS_EUR_PER_MONTH, DEFAULT_GRUNDPREIS_EUR_PER_MONTH),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=1000,
                    step=0.01,
                    unit_of_measurement="EUR/month",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_TARIFF_EFFECTIVE_FROM,
                default=_effective_date_default(defaults),
            ): selector.DateSelector(),
        },
    )


__all__ = [
    "get_options_schema",
]
