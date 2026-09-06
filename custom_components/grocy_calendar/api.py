"""Minimal Grocy objects API client."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientResponseError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


class GrocyApiError(RuntimeError):
    """Raised when Grocy rejects a request."""


class GrocyApi:
    """Call Grocy's generic objects API without exposing credentials."""

    def __init__(self, hass: HomeAssistant, url: str, api_key: str) -> None:
        self._hass = hass
        self._url = url.rstrip("/")
        self._headers = {"GROCY-API-KEY": api_key}

    async def get(self, path: str) -> list[dict[str, Any]]:
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(f"{self._url}/{path}", headers=self._headers, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
        except ClientResponseError as err:
            raise GrocyApiError(f"Grocy GET {path} returned HTTP {err.status}") from err
        if not isinstance(data, list):
            raise GrocyApiError(f"Grocy GET {path} returned an unexpected response")
        return data

    async def post(self, path: str, payload: dict[str, Any]) -> int:
        session = async_get_clientsession(self._hass)
        try:
            async with session.post(f"{self._url}/{path}", headers=self._headers, json=payload, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
        except ClientResponseError as err:
            raise GrocyApiError(f"Grocy POST {path} returned HTTP {err.status}") from err
        created_id = data.get("created_object_id") if isinstance(data, dict) else None
        if isinstance(created_id, str) and created_id.isdecimal():
            created_id = int(created_id)
        if not isinstance(created_id, int) or isinstance(created_id, bool):
            raise GrocyApiError(f"Grocy POST {path} returned no object ID")
        return created_id

    async def delete(self, path: str) -> None:
        session = async_get_clientsession(self._hass)
        try:
            async with session.delete(f"{self._url}/{path}", headers=self._headers, timeout=10) as response:
                response.raise_for_status()
        except ClientResponseError as err:
            raise GrocyApiError(f"Grocy DELETE {path} returned HTTP {err.status}") from err
