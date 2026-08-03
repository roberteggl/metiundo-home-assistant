"""Tests for the Metiundo config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.metiundo.api import MetiundoMeteringPoint
from custom_components.metiundo.const import CONF_ENABLE_EXPORT_METRICS, CONF_METERING_POINT_UUID, DOMAIN
from homeassistant import config_entries, loader
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


def _point(uuid: str, name: str) -> MetiundoMeteringPoint:
    """Build a supported electricity point for flow tests."""
    return MetiundoMeteringPoint(
        uuid=uuid,
        meter_type="electricity",
        name=name,
        description=None,
        address=None,
        sensor_identifier=None,
        available_fields=frozenset({"energyOut", "energyIn"}),
        last_reading=None,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_flow_selects_single_metering_point(hass: HomeAssistant) -> None:
    """A single supported point is stored without an extra flow step."""
    loader.async_setup(hass)
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)
    assert DOMAIN in await loader.async_get_custom_components(hass)
    with patch(
        "custom_components.metiundo.config_flow_handler.config_flow.validate_credentials",
        return_value=[_point("point-1", "Home")],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@example.com", CONF_PASSWORD: "secret"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_METERING_POINT_UUID] == "point-1"
    assert result["options"][CONF_ENABLE_EXPORT_METRICS] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_flow_selects_from_multiple_metering_points(hass: HomeAssistant) -> None:
    """Multiple supported points require an explicit UUID selection."""
    loader.async_setup(hass)
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)
    assert DOMAIN in await loader.async_get_custom_components(hass)
    with patch(
        "custom_components.metiundo.config_flow_handler.config_flow.validate_credentials",
        return_value=[_point("point-1", "Home"), _point("point-2", "Office")],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@example.com", CONF_PASSWORD: "secret"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "metering_point"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_METERING_POINT_UUID: "point-2"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_METERING_POINT_UUID] == "point-2"
