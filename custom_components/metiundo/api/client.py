"""
API Client for Metiundo Smart Meter.

This module provides the API client for communicating with the Metiundo
smart-meter API (https://api.metiundo.de/swagger/openapi.yaml).

The Metiundo API exposes historical 15-minute meter readings (cumulative
grid import/export energy plus timestamps and data-quality information).
It is NOT a live-power API.

Note: The real authentication flow and request implementation are not
implemented yet. `async_get_data()` is a placeholder that returns an empty
payload so the integration scaffold can be set up and validated.

For more information on creating API clients:
https://developers.home-assistant.io/docs/api_lib_index
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any

import aiohttp

from custom_components.metiundo.const import API_BASE_URL


class MetiundoApiClientError(Exception):
    """Base exception to indicate a general API error."""


class MetiundoApiClientCommunicationError(
    MetiundoApiClientError,
):
    """Exception to indicate a communication error with the API."""


class MetiundoApiClientAuthenticationError(
    MetiundoApiClientError,
):
    """Exception to indicate an authentication error with the API."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """
    Verify that the API response is valid.

    Raises appropriate exceptions for authentication and HTTP errors.

    Args:
        response: The aiohttp ClientResponse to verify.

    Raises:
        MetiundoApiClientAuthenticationError: For 401/403 errors.
        aiohttp.ClientResponseError: For other HTTP errors.

    """
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise MetiundoApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


class MetiundoApiClient:
    """
    API Client for the Metiundo smart-meter API.

    The username and password are stored for the upcoming authentication
    implementation (e.g. Basic Auth or token exchange) and would be used to
    build the Authorization headers for every request.

    For more information on API clients:
    https://developers.home-assistant.io/docs/api_lib_index

    Attributes:
        _username: The username for API authentication.
        _password: The password for API authentication.
        _session: The aiohttp ClientSession for making requests.

    """

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """
        Initialize the API Client with credentials.

        Args:
            username: The username for authentication from config flow.
            password: The password for authentication from config flow.
            session: The aiohttp ClientSession to use for requests.

        """
        self._username = username
        self._password = password
        self._session = session

    async def async_get_data(self) -> dict[str, Any]:
        """
        Fetch meter readings from the Metiundo API.

        TODO: Implement the real Metiundo API request (authentication,
        reading selection) once the API contract is known.

        Returns:
            A dictionary containing the meter data.

        Raises:
            MetiundoApiClientAuthenticationError: If authentication fails.
            MetiundoApiClientCommunicationError: If communication fails.
            MetiundoApiClientError: For other API errors.

        """
        return {}

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """
        Wrapper for API requests with error handling.

        This method handles all HTTP requests and translates exceptions
        into integration-specific exceptions.

        Args:
            method: The HTTP method (get, post, patch, etc.).
            url: The URL to request.
            data: Optional data to send in the request body.
            headers: Optional headers to include in the request.

        Returns:
            The JSON response from the API.

        Raises:
            MetiundoApiClientAuthenticationError: If authentication fails.
            MetiundoApiClientCommunicationError: If communication fails.
            MetiundoApiClientError: For other API errors.

        """
        try:
            async with asyncio.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=f"{API_BASE_URL}{url}",
                    headers=headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise MetiundoApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise MetiundoApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:
            msg = f"Something really wrong happened! - {exception}"
            raise MetiundoApiClientError(
                msg,
            ) from exception
