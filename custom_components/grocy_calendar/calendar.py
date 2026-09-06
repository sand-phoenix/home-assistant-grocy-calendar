"""Read-only calendar entity backed by Grocy meal plans."""

from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import CONF_API_KEY, CONF_URL


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up the calendar platform."""
    async_add_entities([GrocyMealPlanCalendar(hass, entry)])


class GrocyMealPlanCalendar(CalendarEntity):
    """Expose Grocy meal-plan rows as all-day calendar events."""

    _attr_has_entity_name = True
    _attr_name = "Meal Plan"
    _attr_initial_color = "#5c6bc0"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._url = entry.data[CONF_URL].rstrip("/")
        self._api_key = entry.data[CONF_API_KEY]
        self._attr_unique_id = entry.entry_id
        self._events: list[CalendarEvent] = []

    async def _get(self, path: str) -> list[dict]:
        session = async_get_clientsession(self._hass)
        async with session.get(f"{self._url}/{path}", headers={"GROCY-API-KEY": self._api_key}, timeout=10) as response:
            response.raise_for_status()
            data = await response.json()
        if not isinstance(data, list):
            raise ValueError(f"Grocy {path} response was not a list")
        return data

    async def async_update(self) -> None:
        """Fetch meal plans and their recipe names without writing to Grocy."""
        meal_plan, recipes = await self._get("objects/meal_plan"), await self._get("objects/recipes")
        recipe_names = {item["id"]: item["name"] for item in recipes if "id" in item and "name" in item}
        events: list[CalendarEvent] = []
        for item in meal_plan:
            try:
                start = date.fromisoformat(item["day"])
            except (KeyError, TypeError, ValueError):
                continue
            summary = recipe_names.get(item.get("recipe_id")) or item.get("note") or "Meal"
            events.append(CalendarEvent(start=start, end=start + timedelta(days=1), summary=str(summary), uid=f"grocy-meal-plan-{item.get('id')}", description=item.get("note")))
        self._events = sorted(events, key=lambda event: event.start)

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        return next((event for event in self._events if event.end > today), None)

    async def async_get_events(self, hass: HomeAssistant, start_date, end_date) -> list[CalendarEvent]:
        return [event for event in self._events if event.end > start_date.date() and event.start < end_date.date()]
