"""Tests for the Metiundo API client."""

from __future__ import annotations

from typing import Any, Self

import pytest

from custom_components.metiundo.api import (
    MetiundoApiClient,
    MetiundoApiClientAuthenticationError,
    MetiundoApiClientRateLimitError,
)


class FakeResponse:
    """Minimal async response implementation used by the API client tests."""

    def __init__(self, status: int, payload: Any = None, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.payload = payload
        self.headers = headers or {}

    async def __aenter__(self) -> Self:
        """Enter the fake response context manager."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the fake response context manager."""

    async def json(self, **kwargs: Any) -> Any:
        """Return the configured JSON payload."""
        return self.payload

    async def text(self) -> str:
        """Return a string representation for error responses."""
        return str(self.payload)


class FakeSession:
    """Minimal session implementation that records requests."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str, dict[str, Any]]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        """Return the next configured response."""
        self.requests.append((method, url, kwargs))
        return self.responses.pop(0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_and_metering_points() -> None:
    """Login sends email credentials and lists accessible points."""
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"tokens": {"accessToken": "access", "refreshToken": "refresh"}},
            ),
            FakeResponse(
                200,
                [
                    {
                        "uuid": "point-1",
                        "meterType": "electricity",
                        "name": "Home",
                        "availableFields": ["energyOut", "energyIn"],
                    },
                ],
            ),
        ],
    )
    client = MetiundoApiClient("user@example.com", "secret", session)  # type: ignore[arg-type]

    points = await client.async_get_metering_points()

    assert points[0].uuid == "point-1"
    assert session.requests[0][1] == "https://api.metiundo.de/v1/auth/login"
    assert session.requests[0][2]["json"] == {"email": "user@example.com", "password": "secret"}
    assert session.requests[1][2]["headers"]["Authorization"] == "Bearer access"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refreshes_access_token_after_unauthorized_response() -> None:
    """An expired access token is refreshed and the original request retried."""
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"tokens": {"accessToken": "old-access", "refreshToken": "old-refresh"}},
            ),
            FakeResponse(401),
            FakeResponse(200, {"accessToken": "new-access", "refreshToken": "new-refresh"}),
            FakeResponse(200, []),
        ],
    )
    client = MetiundoApiClient("user@example.com", "secret", session)  # type: ignore[arg-type]
    await client.async_login()

    assert await client.async_get_metering_points() == []
    assert session.requests[2][1] == "https://api.metiundo.de/v1/auth/refresh"
    assert session.requests[3][2]["headers"]["Authorization"] == "Bearer new-access"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_login_raises_authentication_error() -> None:
    """Invalid login credentials are mapped to an authentication error."""
    session = FakeSession([FakeResponse(401)])
    client = MetiundoApiClient("user@example.com", "secret", session)  # type: ignore[arg-type]

    with pytest.raises(MetiundoApiClientAuthenticationError):
        await client.async_login()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_includes_retry_after() -> None:
    """HTTP 429 is mapped to a rate-limit error."""
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"tokens": {"accessToken": "access", "refreshToken": "refresh"}},
            ),
            FakeResponse(429, headers={"Retry-After": "30"}),
        ],
    )
    client = MetiundoApiClient("user@example.com", "secret", session)  # type: ignore[arg-type]
    await client.async_login()

    with pytest.raises(MetiundoApiClientRateLimitError) as error:
        await client.async_get_metering_points()

    assert error.value.retry_after == 30


@pytest.mark.unit
@pytest.mark.asyncio
async def test_latest_reading_accepts_wrapped_response() -> None:
    """Beta API response wrappers are normalized to one reading."""
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"tokens": {"accessToken": "access", "refreshToken": "refresh"}},
            ),
            FakeResponse(
                200,
                {
                    "reading": {
                        "readingTime": 1_663_344_900_000,
                        "energyOut": 578_216_900,
                    },
                },
            ),
        ],
    )
    client = MetiundoApiClient("user@example.com", "secret", session)  # type: ignore[arg-type]

    reading = await client.async_get_latest_reading("point-1")

    assert reading.energy_out_kwh == pytest.approx(578.2169)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_readings_uses_historical_range_endpoint() -> None:
    """Historical readings use the documented from/to query parameters."""
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"tokens": {"accessToken": "access", "refreshToken": "refresh"}},
            ),
            FakeResponse(
                200,
                [{"readingTime": 1_663_344_900_000, "energyOut": 100}],
            ),
        ],
    )
    client = MetiundoApiClient("user@example.com", "secret", session)  # type: ignore[arg-type]

    readings = await client.async_get_readings("point-1", 100, 200)

    assert len(readings) == 1
    assert session.requests[1][1].endswith("/meteringpoints/point-1/readings")
    assert session.requests[1][2]["params"] == {"from": 100, "to": 200}
