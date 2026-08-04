"""
Config flow schemas.

Schemas for the main configuration flow steps:
- User setup
- Reconfiguration
- Reauthentication

When this file grows too large (>300 lines), consider splitting into:
- user.py: User setup schemas
- reauth.py: Reauthentication schemas
- reconfigure.py: Reconfiguration schemas
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import voluptuous as vol

from custom_components.metiundo.api import MetiundoMeteringPoint
from custom_components.metiundo.const import (
    CONF_ARBEITSPREIS_CT_PER_KWH,
    CONF_ENABLE_COST_METRICS,
    CONF_ENABLE_EXPORT_METRICS,
    CONF_HISTORY_START_DATE,
    CONF_IMPORT_HISTORICAL_DATA,
    CONF_METERING_POINT_UUID,
    DEFAULT_ARBEITSPREIS_CT_PER_KWH,
    DEFAULT_ENABLE_COST_METRICS,
    DEFAULT_ENABLE_EXPORT_METRICS,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector


def get_user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """
    Get schema for user step (initial setup).

    Args:
        defaults: Optional dictionary of default values to pre-populate the form.

    Returns:
        Voluptuous schema for user credentials input.

    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME,
                default=defaults.get(CONF_USERNAME, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                ),
            ),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                ),
            ),
            vol.Optional(
                CONF_ENABLE_EXPORT_METRICS,
                default=DEFAULT_ENABLE_EXPORT_METRICS,
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_IMPORT_HISTORICAL_DATA,
                default=False,
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_COST_METRICS,
                default=DEFAULT_ENABLE_COST_METRICS,
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ARBEITSPREIS_CT_PER_KWH,
                default=DEFAULT_ARBEITSPREIS_CT_PER_KWH,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=0.01,
                    unit_of_measurement="ct/kWh",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        },
    )


def get_reconfigure_schema(username: str) -> vol.Schema:
    """
    Get schema for reconfigure step.

    Args:
        username: Current username to pre-fill in the form.

    Returns:
        Voluptuous schema for reconfiguration.

    """
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME,
                default=username,
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                ),
            ),
            vol.Required(
                CONF_PASSWORD,
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                ),
            ),
        },
    )


def get_history_schema() -> vol.Schema:
    """Get schema for the one-time historical import date."""
    return vol.Schema(
        {
            vol.Required(CONF_HISTORY_START_DATE): selector.DateSelector(),
        },
    )


def get_reauth_schema(username: str) -> vol.Schema:
    """
    Get schema for reauthentication step.

    Args:
        username: Current username to pre-fill in the form.

    Returns:
        Voluptuous schema for reauthentication.

    """
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME,
                default=username,
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                ),
            ),
            vol.Required(
                CONF_PASSWORD,
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                ),
            ),
        },
    )


def get_metering_point_schema(points: Sequence[MetiundoMeteringPoint]) -> vol.Schema:
    """Get a schema for selecting one accessible electricity metering point."""
    options = [
        selector.SelectOptionDict(
            value=point.uuid,
            label=point.name,
        )
        for point in points
    ]
    return vol.Schema(
        {
            vol.Required(CONF_METERING_POINT_UUID): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                ),
            ),
        },
    )


__all__ = [
    "get_history_schema",
    "get_metering_point_schema",
    "get_reauth_schema",
    "get_reconfigure_schema",
    "get_user_schema",
]
