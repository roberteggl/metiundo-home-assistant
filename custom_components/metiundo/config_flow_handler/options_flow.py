"""
Options flow for metiundo.

This module implements the options flow that allows users to modify settings
after the initial configuration, such as update intervals and debug settings.

For more information:
https://developers.home-assistant.io/docs/config_entries_options_flow_handler
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from custom_components.metiundo.config_flow_handler.schemas import get_options_schema
from custom_components.metiundo.const import (
    CONF_ARBEITSPREIS_CT_PER_KWH,
    CONF_ENABLE_COST_METRICS,
    CONF_GRUNDPREIS_EUR_PER_MONTH,
    CONF_TARIFF_EFFECTIVE_FROM,
    CONF_TARIFFS,
)
from homeassistant import config_entries


def _parse_effective_date(value: Any) -> date | None:
    """Parse a tariff date and normalize it to the first of its month."""
    if isinstance(value, date):
        return value.replace(day=1)
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).replace(day=1)
        except ValueError:
            return None
    return None


def _is_month_start(value: Any) -> bool:
    """Return whether a tariff date is the first day of its month."""
    if isinstance(value, date):
        return value.day == 1
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).day == 1
        except ValueError:
            return False
    return False


def _stored_tariffs(options: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Read the tariff list, falling back to the original single-tariff options."""
    raw_tariffs = options.get(CONF_TARIFFS)
    if isinstance(raw_tariffs, list):
        tariffs = raw_tariffs
    elif options.get(CONF_ENABLE_COST_METRICS, False):
        tariffs = [
            {
                CONF_TARIFF_EFFECTIVE_FROM: options.get(CONF_TARIFF_EFFECTIVE_FROM),
                CONF_ARBEITSPREIS_CT_PER_KWH: options.get(CONF_ARBEITSPREIS_CT_PER_KWH),
                CONF_GRUNDPREIS_EUR_PER_MONTH: options.get(CONF_GRUNDPREIS_EUR_PER_MONTH),
            },
        ]
    else:
        tariffs = []

    normalized: list[dict[str, Any]] = []
    for tariff in tariffs:
        if not isinstance(tariff, Mapping):
            continue
        effective_date = _parse_effective_date(tariff.get(CONF_TARIFF_EFFECTIVE_FROM))
        arbeitspreis = tariff.get(CONF_ARBEITSPREIS_CT_PER_KWH)
        grundpreis = tariff.get(CONF_GRUNDPREIS_EUR_PER_MONTH)
        if (
            effective_date is None
            or isinstance(arbeitspreis, bool)
            or not isinstance(arbeitspreis, (int, float))
            or arbeitspreis < 0
            or isinstance(grundpreis, bool)
            or not isinstance(grundpreis, (int, float))
            or grundpreis < 0
        ):
            continue
        normalized.append(
            {
                CONF_TARIFF_EFFECTIVE_FROM: effective_date.isoformat(),
                CONF_ARBEITSPREIS_CT_PER_KWH: float(arbeitspreis),
                CONF_GRUNDPREIS_EUR_PER_MONTH: float(grundpreis),
            },
        )
    return normalized


def _upsert_tariff(options: Mapping[str, Any], user_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Add or replace the tariff for its effective month."""
    effective_date = _parse_effective_date(user_input.get(CONF_TARIFF_EFFECTIVE_FROM))
    assert effective_date is not None
    effective_from = effective_date.isoformat()
    tariffs = [tariff for tariff in _stored_tariffs(options) if tariff[CONF_TARIFF_EFFECTIVE_FROM] != effective_from]
    tariffs.append(
        {
            CONF_TARIFF_EFFECTIVE_FROM: effective_from,
            CONF_ARBEITSPREIS_CT_PER_KWH: float(user_input[CONF_ARBEITSPREIS_CT_PER_KWH]),
            CONF_GRUNDPREIS_EUR_PER_MONTH: float(user_input[CONF_GRUNDPREIS_EUR_PER_MONTH]),
        },
    )
    return sorted(tariffs, key=lambda tariff: tariff[CONF_TARIFF_EFFECTIVE_FROM])


class MetiundoOptionsFlow(config_entries.OptionsFlow):
    """
    Handle options flow for the integration.

    This class manages the options that users can modify after initial setup,
    such as update intervals and debug settings.

    The options flow always starts with async_step_init and provides a single
    form for all configurable options.

    For more information:
    https://developers.home-assistant.io/docs/config_entries_options_flow_handler
    """

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Manage the options for the integration.

        This is the entry point for the options flow, allowing users to
        configure advanced settings like update interval and debugging.

        Args:
            user_input: The user input from the options form, or None for initial display.

        Returns:
            The config flow result, either showing a form or creating an options entry.

        """
        if user_input is not None:
            errors: dict[str, str] = {}
            effective_date = _parse_effective_date(user_input.get(CONF_TARIFF_EFFECTIVE_FROM))
            if user_input.get(CONF_ENABLE_COST_METRICS, False) and (
                effective_date is None or not _is_month_start(user_input.get(CONF_TARIFF_EFFECTIVE_FROM))
            ):
                errors["base"] = "tariff_must_start_first_of_month"
            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=get_options_schema(self.config_entry.options),
                    errors=errors,
                )

            options = dict(user_input)
            if user_input.get(CONF_ENABLE_COST_METRICS, False):
                options[CONF_TARIFFS] = _upsert_tariff(self.config_entry.options, user_input)
            else:
                options[CONF_TARIFFS] = _stored_tariffs(self.config_entry.options)
            options.pop(CONF_ARBEITSPREIS_CT_PER_KWH, None)
            options.pop(CONF_GRUNDPREIS_EUR_PER_MONTH, None)
            options.pop(CONF_TARIFF_EFFECTIVE_FROM, None)
            return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="init",
            data_schema=get_options_schema(self.config_entry.options),
        )


__all__ = ["MetiundoOptionsFlow"]
