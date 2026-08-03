"""Config flow for the Metiundo account and selected metering point."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from custom_components.metiundo.api import MetiundoApiClientError, MetiundoMeteringPoint
from custom_components.metiundo.config_flow_handler.schemas import (
    get_history_schema,
    get_metering_point_schema,
    get_reauth_schema,
    get_reconfigure_schema,
    get_user_schema,
)
from custom_components.metiundo.config_flow_handler.validators import validate_credentials
from custom_components.metiundo.const import (
    CONF_ARBEITSPREIS_CT_PER_KWH,
    CONF_ENABLE_COST_METRICS,
    CONF_ENABLE_EXPORT_METRICS,
    CONF_GRUNDPREIS_EUR_PER_MONTH,
    CONF_HISTORY_START_DATE,
    CONF_IMPORT_HISTORICAL_DATA,
    CONF_METERING_POINT_UUID,
    CONF_TARIFF_EFFECTIVE_FROM,
    CONF_TARIFFS,
    DEFAULT_ENABLE_EXPORT_METRICS,
    DOMAIN,
    LOGGER,
)
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.loader import async_get_loaded_integration

if TYPE_CHECKING:
    from collections.abc import Sequence

    from homeassistant.config_entries import ConfigEntry

ERROR_MAP = {
    "MetiundoApiClientAccessError": "connection",
    "MetiundoApiClientAuthenticationError": "auth",
    "MetiundoApiClientCommunicationError": "connection",
}


def _tariff_date(value: Any) -> date | None:
    """Return a tariff effective date from config-flow input."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


class MetiundoConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle setup, metering-point selection, reconfiguration, and reauth."""

    VERSION = 1

    _pending_credentials: dict[str, Any] | None = None
    _pending_options: dict[str, Any] = {}
    _pending_points: list[MetiundoMeteringPoint] = []
    _pending_entry: ConfigEntry[Any] | None = None

    def __init__(self) -> None:
        """Initialize per-flow state used by the metering-point step."""
        super().__init__()
        self._pending_credentials = None
        self._pending_options = {}
        self._pending_points = []
        self._pending_entry = None

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> Any:
        """Return the options flow."""
        from custom_components.metiundo.config_flow_handler.options_flow import MetiundoOptionsFlow  # noqa: PLC0415

        return MetiundoOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle initial account setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            tariff_date = _tariff_date(user_input.get(CONF_TARIFF_EFFECTIVE_FROM))
            if user_input.get(CONF_ENABLE_COST_METRICS, False) and (tariff_date is None or tariff_date.day != 1):
                return self._show_user_form({"base": "tariff_must_start_first_of_month"})
            try:
                points = await validate_credentials(
                    self.hass,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except MetiundoApiClientError as exception:
                errors["base"] = self._map_exception_to_error(exception)
            else:
                await self.async_set_unique_id(self._normalize_unique_id(user_input[CONF_USERNAME]))
                self._abort_if_unique_id_configured()
                credentials = {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }
                options = {
                    CONF_ENABLE_EXPORT_METRICS: user_input.get(
                        CONF_ENABLE_EXPORT_METRICS,
                        DEFAULT_ENABLE_EXPORT_METRICS,
                    ),
                }
                if user_input.get(CONF_IMPORT_HISTORICAL_DATA, False):
                    options[CONF_IMPORT_HISTORICAL_DATA] = True
                if user_input.get(CONF_ENABLE_COST_METRICS, False):
                    assert tariff_date is not None
                    options[CONF_ENABLE_COST_METRICS] = True
                    options[CONF_TARIFFS] = [
                        {
                            CONF_TARIFF_EFFECTIVE_FROM: tariff_date.isoformat(),
                            CONF_ARBEITSPREIS_CT_PER_KWH: user_input[CONF_ARBEITSPREIS_CT_PER_KWH],
                            CONF_GRUNDPREIS_EUR_PER_MONTH: user_input[CONF_GRUNDPREIS_EUR_PER_MONTH],
                        },
                    ]
                return self._prepare_point_selection(credentials, points, options)

        return self._show_user_form(errors)

    async def async_step_metering_point(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle selection of one metering point after authentication."""
        if self._pending_credentials is None or not self._pending_points:
            return self.async_abort(reason="unknown")

        if user_input is None:
            return self._show_point_form()

        selected_uuid = user_input.get(CONF_METERING_POINT_UUID)
        if not isinstance(selected_uuid, str) or selected_uuid not in {point.uuid for point in self._pending_points}:
            return self._show_point_form(errors={"base": "invalid_metering_point"})

        if self._pending_entry is None:
            return self.async_create_entry(
                title=self._pending_credentials[CONF_USERNAME],
                data={
                    **self._pending_credentials,
                    CONF_METERING_POINT_UUID: selected_uuid,
                },
                options=self._pending_options,
            )

        entry_data = {
            **self._pending_entry.data,
            **self._pending_credentials,
            CONF_METERING_POINT_UUID: selected_uuid,
        }
        return self.async_update_reload_and_abort(self._pending_entry, data=entry_data)

    async def async_step_history(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the optional one-time historical import date."""
        if self._pending_credentials is None or not self._pending_points:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}
        if user_input is not None:
            raw_date = user_input.get(CONF_HISTORY_START_DATE)
            try:
                start_date = raw_date if isinstance(raw_date, date) else date.fromisoformat(str(raw_date))
            except ValueError:
                errors["base"] = "invalid_history_start_date"
            else:
                latest_allowed_date = (datetime.now(UTC) - timedelta(hours=48)).date()
                if start_date > latest_allowed_date:
                    errors["base"] = "history_start_date_too_recent"
                else:
                    self._pending_options[CONF_HISTORY_START_DATE] = start_date.isoformat()
                    return self._show_or_create_point_entry()

        return self.async_show_form(
            step_id="history",
            data_schema=get_history_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle credential and metering-point reconfiguration."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                points = await validate_credentials(
                    self.hass,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except MetiundoApiClientError as exception:
                errors["base"] = self._map_exception_to_error(exception)
            else:
                return self._prepare_existing_entry(entry, user_input, points)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_reconfigure_schema(entry.data.get(CONF_USERNAME, "")),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Start the reauthentication flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle updated credentials after authentication failure."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                points = await validate_credentials(
                    self.hass,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except MetiundoApiClientError as exception:
                errors["base"] = self._map_exception_to_error(exception)
            else:
                return self._prepare_existing_entry(entry, user_input, points)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=get_reauth_schema(entry.data.get(CONF_USERNAME, "")),
            errors=errors,
            description_placeholders={"username": entry.data.get(CONF_USERNAME, "")},
        )

    def _prepare_point_selection(
        self,
        credentials: dict[str, Any],
        points: Sequence[MetiundoMeteringPoint],
        options: dict[str, Any],
    ) -> config_entries.ConfigFlowResult:
        """Create an entry immediately or show the point selector."""
        eligible_points = self._eligible_points(points)
        if not eligible_points:
            return self.async_abort(reason="no_metering_points")
        self._pending_credentials = credentials
        self._pending_options = options
        self._pending_points = eligible_points
        self._pending_entry = None
        if options.get(CONF_IMPORT_HISTORICAL_DATA, False):
            return self.async_show_form(
                step_id="history",
                data_schema=get_history_schema(),
            )
        return self._show_or_create_point_entry()

    def _show_or_create_point_entry(self) -> config_entries.ConfigFlowResult:
        """Show point selection or create the entry when only one point exists."""
        assert self._pending_credentials is not None
        if len(self._pending_points) == 1:
            return self.async_create_entry(
                title=self._pending_credentials[CONF_USERNAME],
                data={
                    **self._pending_credentials,
                    CONF_METERING_POINT_UUID: self._pending_points[0].uuid,
                },
                options=self._pending_options,
            )
        return self._show_point_form()

    def _prepare_existing_entry(
        self,
        entry: ConfigEntry[Any],
        credentials: dict[str, Any],
        points: Sequence[MetiundoMeteringPoint],
    ) -> config_entries.ConfigFlowResult:
        """Update credentials while preserving a valid selected point."""
        eligible_points = self._eligible_points(points)
        if not eligible_points:
            return self.async_abort(reason="no_metering_points")

        selected_uuid = entry.data.get(CONF_METERING_POINT_UUID)
        if selected_uuid in {point.uuid for point in eligible_points}:
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, **credentials},
            )
        if len(eligible_points) == 1:
            return self.async_update_reload_and_abort(
                entry,
                data={
                    **entry.data,
                    **credentials,
                    CONF_METERING_POINT_UUID: eligible_points[0].uuid,
                },
            )

        self._pending_credentials = credentials
        self._pending_points = eligible_points
        self._pending_entry = entry
        return self._show_point_form()

    def _show_user_form(self, errors: dict[str, str]) -> config_entries.ConfigFlowResult:
        """Show the initial credentials form."""
        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, "Integration documentation URL is not set in manifest.json"
        return self.async_show_form(
            step_id="user",
            data_schema=get_user_schema(),
            errors=errors,
            description_placeholders={"documentation_url": integration.documentation},
        )

    def _show_point_form(self, errors: dict[str, str] | None = None) -> config_entries.ConfigFlowResult:
        """Show the metering-point selector."""
        return self.async_show_form(
            step_id="metering_point",
            data_schema=get_metering_point_schema(self._pending_points),
            errors=errors or {},
        )

    @staticmethod
    def _eligible_points(points: Sequence[MetiundoMeteringPoint]) -> list[MetiundoMeteringPoint]:
        """Filter the API response to points supported by this integration."""
        return [
            point
            for point in points
            if point.meter_type in {"electricity", "electricity_iot"} and point.supports_energy
        ]

    @staticmethod
    def _normalize_unique_id(username: str) -> str:
        """Normalize the account email for config-entry uniqueness."""
        return username.strip().casefold()

    def _map_exception_to_error(self, exception: Exception) -> str:
        """Map API exceptions to user-facing error keys."""
        LOGGER.warning("Error in config flow: %s", exception)
        return ERROR_MAP.get(type(exception).__name__, "unknown")


__all__ = ["MetiundoConfigFlowHandler"]
