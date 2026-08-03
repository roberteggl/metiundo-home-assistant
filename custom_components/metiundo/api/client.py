"""Async API client for the Metiundo readings API."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
import socket
from typing import Any

import aiohttp

from custom_components.metiundo.const import API_BASE_URL, API_TIMEOUT_SECONDS, LOGGER

from .models import MetiundoMeteringPoint, MetiundoReading


class MetiundoApiClientError(Exception):
    """Base exception for Metiundo API failures."""


class MetiundoApiClientCommunicationError(MetiundoApiClientError):
    """Exception for network, timeout, and server failures."""


class MetiundoApiClientAuthenticationError(MetiundoApiClientError):
    """Exception for invalid or expired credentials."""


class MetiundoApiClientAccessError(MetiundoApiClientError):
    """Exception when the account cannot access a requested resource."""


class MetiundoApiClientRateLimitError(MetiundoApiClientError):
    """Exception raised when the API rate limit has been exceeded."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        """Initialize a rate-limit error."""
        super().__init__(message)
        self.retry_after = retry_after


class MetiundoApiClient:
    """Client for authentication and metering-point readings."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        enable_debugging: bool = False,
    ) -> None:
        """Initialize the client with the account email and password."""
        self._username = username
        self._password = password
        self._session = session
        self._enable_debugging = enable_debugging
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    async def async_login(self) -> None:
        """Authenticate and store the returned tokens in memory."""
        payload = await self._request_json(
            "POST",
            "/auth/login",
            data={"email": self._username, "password": self._password},
            authenticated=False,
        )
        self._set_tokens(payload)

    async def async_get_metering_points(self) -> list[MetiundoMeteringPoint]:
        """Return all metering points accessible to the account."""
        await self._ensure_authenticated()
        payload = await self._request_json("GET", "/meteringpoints")
        if not isinstance(payload, list):
            raise MetiundoApiClientError("Invalid metering point response")
        if not all(isinstance(item, Mapping) for item in payload):
            raise MetiundoApiClientError("Invalid metering point response")

        try:
            return [MetiundoMeteringPoint.from_api(item) for item in payload]
        except (TypeError, ValueError) as exception:
            raise MetiundoApiClientError("Invalid metering point response") from exception

    async def async_get_metering_point(self, identifier: str) -> MetiundoMeteringPoint:
        """Return one accessible metering point by UUID."""
        await self._ensure_authenticated()
        payload = await self._request_json("GET", f"/meteringpoints/{identifier}")
        if not isinstance(payload, Mapping):
            raise MetiundoApiClientError("Invalid metering point response")
        try:
            return MetiundoMeteringPoint.from_api(payload)
        except ValueError as exception:
            raise MetiundoApiClientError("Invalid metering point response") from exception

    async def async_get_latest_reading(self, identifier: str) -> MetiundoReading:
        """Return the reading closest to the current time."""
        await self._ensure_authenticated()
        timestamp = int(datetime.now(UTC).timestamp() * 1000)
        payload = await self._request_json(
            "GET",
            f"/meteringpoints/{identifier}/reading",
            params={"timestamp": timestamp},
        )
        readings = self._parse_readings(payload)

        readings = [reading for reading in readings if reading.reading_time is not None]
        if not readings:
            raise MetiundoApiClientError("The metering point has no readings")
        return max(
            readings,
            key=lambda reading: (
                reading.reading_time if reading.reading_time is not None else datetime.min.replace(tzinfo=UTC)
            ),
        )

    async def async_get_readings(
        self,
        identifier: str,
        from_timestamp: int,
        to_timestamp: int,
        *,
        align_iot_readings: bool = False,
    ) -> list[MetiundoReading]:
        """Return readings in an inclusive/exclusive millisecond time range."""
        await self._ensure_authenticated()
        params: dict[str, str | int] = {
            "from": from_timestamp,
            "to": to_timestamp,
        }
        if align_iot_readings:
            params["alignIotReadings"] = "true"
        payload = await self._request_json(
            "GET",
            f"/meteringpoints/{identifier}/readings",
            params=params,
        )
        return self._parse_readings(payload)

    @staticmethod
    def _extract_readings(payload: Any) -> list[Mapping[str, Any]]:
        """Accept the documented array and beta API response wrappers."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, Mapping):
            if "readingTime" in payload:
                return [payload]
            for key in ("reading", "readings", "data"):
                wrapped = payload.get(key)
                if isinstance(wrapped, Mapping):
                    return [wrapped]
                if isinstance(wrapped, list):
                    return wrapped
        raise MetiundoApiClientError("Invalid reading response")

    @classmethod
    def _parse_readings(cls, payload: Any) -> list[MetiundoReading]:
        """Validate and parse a response containing one or more readings."""
        payload = cls._extract_readings(payload)
        if not all(isinstance(item, Mapping) for item in payload):
            raise MetiundoApiClientError("Invalid reading response")
        try:
            return [MetiundoReading.from_api(item) for item in payload]
        except (TypeError, ValueError) as exception:
            raise MetiundoApiClientError("Invalid reading response") from exception

    async def async_get_data(self, identifier: str) -> MetiundoReading:
        """Compatibility method used by the coordinator to fetch the latest data."""
        return await self.async_get_latest_reading(identifier)

    async def _ensure_authenticated(self) -> None:
        """Log in lazily when the client has no access token."""
        if self._access_token is None:
            await self.async_login()

    async def _async_refresh_or_login(self) -> None:
        """Refresh the access token, falling back to a fresh login if needed."""
        if self._refresh_token is None:
            await self.async_login()
            return

        try:
            payload = await self._request_json(
                "POST",
                "/auth/refresh",
                data={"refreshToken": self._refresh_token},
                authenticated=False,
            )
        except MetiundoApiClientAuthenticationError:
            await self.async_login()
        else:
            self._set_tokens(payload)

    def _set_tokens(self, payload: Any) -> None:
        """Validate and store an authentication response."""
        if not isinstance(payload, Mapping):
            raise MetiundoApiClientAuthenticationError("Invalid authentication response")

        tokens = payload.get("tokens", payload)
        if not isinstance(tokens, Mapping):
            raise MetiundoApiClientAuthenticationError("Invalid authentication response")

        access_token = tokens.get("accessToken")
        refresh_token = tokens.get("refreshToken")
        if not isinstance(access_token, str) or not isinstance(refresh_token, str):
            raise MetiundoApiClientAuthenticationError("Invalid authentication response")
        self._access_token = access_token
        self._refresh_token = refresh_token

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, str] | None = None,
        params: Mapping[str, str | int] | None = None,
        authenticated: bool = True,
        retry_auth: bool = True,
    ) -> Any:
        """Make one request and translate transport/API failures."""
        headers = {"Accept": "application/json"}
        if self._enable_debugging:
            LOGGER.debug("Requesting Metiundo API endpoint %s %s", method, path)
        if authenticated:
            if self._access_token is None:
                raise MetiundoApiClientAuthenticationError("Client is not authenticated")
            headers["Authorization"] = f"Bearer {self._access_token}"

        try:
            async with asyncio.timeout(API_TIMEOUT_SECONDS):
                async with self._session.request(
                    method,
                    f"{API_BASE_URL}{path}",
                    headers=headers,
                    json=data,
                    params=params,
                ) as response:
                    if response.status == 401:
                        if authenticated and retry_auth:
                            await self._async_refresh_or_login()
                            return await self._request_json(
                                method,
                                path,
                                data=data,
                                params=params,
                                authenticated=True,
                                retry_auth=False,
                            )
                        raise MetiundoApiClientAuthenticationError("Invalid or expired credentials")
                    if response.status == 403:
                        if authenticated:
                            raise MetiundoApiClientAccessError("The account cannot access this resource")
                        raise MetiundoApiClientAuthenticationError("Invalid credentials")
                    if response.status == 429:
                        retry_after = self._parse_retry_after(response.headers.get("Retry-After"))
                        raise MetiundoApiClientRateLimitError("Metiundo API rate limit exceeded", retry_after)
                    if response.status >= 500:
                        raise MetiundoApiClientCommunicationError(
                            f"Metiundo API server returned HTTP {response.status}"
                        )
                    if response.status >= 400:
                        detail = (await response.text())[:200]
                        self._raise_http_error(response.status, detail)
                    try:
                        return await response.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError) as exception:
                        raise MetiundoApiClientError("Metiundo API returned invalid JSON") from exception
        except MetiundoApiClientError:
            raise
        except TimeoutError as exception:
            raise MetiundoApiClientCommunicationError("Timed out communicating with Metiundo API") from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise MetiundoApiClientCommunicationError("Error communicating with Metiundo API") from exception

    @staticmethod
    def _parse_retry_after(value: str | None) -> int | None:
        """Parse a numeric Retry-After header when supplied by the API."""
        if value is None:
            return None
        try:
            return max(1, int(value))
        except ValueError:
            return None

    @staticmethod
    def _raise_http_error(status: int, detail: str) -> None:
        """Raise the generic error used for non-special HTTP statuses."""
        raise MetiundoApiClientError(f"Metiundo API returned HTTP {status}: {detail}")
