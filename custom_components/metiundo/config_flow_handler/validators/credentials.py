"""
Credential validators.

Validation functions for user credentials and authentication.

When this file grows, consider splitting into:
- credentials.py: Basic credential validation
- oauth.py: OAuth-specific validation
- api_auth.py: API authentication methods
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.metiundo.api import MetiundoApiClient, MetiundoMeteringPoint
from homeassistant.helpers.aiohttp_client import async_create_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def validate_credentials(
    hass: HomeAssistant,
    username: str,
    password: str,
) -> list[MetiundoMeteringPoint]:
    """
    Validate user credentials by testing API connection.

    Args:
        hass: Home Assistant instance.
        username: The username to validate.
        password: The password to validate.

    Returns:
        Metering points accessible with the credentials.

    Raises:
        MetiundoApiClientAuthenticationError: If credentials are invalid.
        MetiundoApiClientCommunicationError: If communication fails.
        MetiundoApiClientError: For other API errors.

    """
    client = MetiundoApiClient(
        username=username,
        password=password,
        session=async_create_clientsession(hass),
    )
    await client.async_login()
    return await client.async_get_metering_points()


__all__ = [
    "validate_credentials",
]
