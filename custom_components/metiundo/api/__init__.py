"""
API package for metiundo.

Architecture:
    Three-layer data flow: Entities → Coordinator → API Client.
    Only the coordinator should call the API client. Entities must never
    import or call the API client directly.

Exception hierarchy:
    MetiundoApiClientError (base)
    ├── MetiundoApiClientCommunicationError (network/timeout)
    └── MetiundoApiClientAuthenticationError (401/403)

Coordinator exception mapping:
    ApiClientAuthenticationError → ConfigEntryAuthFailed (triggers reauth)
    ApiClientCommunicationError → UpdateFailed (auto-retry)
    ApiClientError             → UpdateFailed (auto-retry)
"""

from .client import (
    MetiundoApiClient,
    MetiundoApiClientAuthenticationError,
    MetiundoApiClientCommunicationError,
    MetiundoApiClientError,
)

__all__ = [
    "MetiundoApiClient",
    "MetiundoApiClientAuthenticationError",
    "MetiundoApiClientCommunicationError",
    "MetiundoApiClientError",
]
