"""Grocy Meal Plan Calendar integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import voluptuous as vol

from .api import GrocyApi, GrocyApiError
from .const import CONF_API_KEY, CONF_URL, DATA_CLIENT, DOMAIN, MEAL_PLAN_SECTION, PLATFORMS, SERVICE_SET_DAY_PLAN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Grocy calendar from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_CLIENT: GrocyApi(hass, entry.data[CONF_URL], entry.data[CONF_API_KEY])}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_DAY_PLAN):
        hass.services.async_register(DOMAIN, SERVICE_SET_DAY_PLAN, lambda call: _async_set_day_plan(hass, call.data), schema=vol.Schema({
            vol.Required("day"): str,
            vol.Required("meal_type"): vol.In({"recipe", "kyo", "takeout"}),
            vol.Optional("main_dish", default=""): str,
            vol.Optional("side_dish", default=""): str,
            vol.Optional("cooking_assignee", default=""): str,
            vol.Optional("dishes_assignee", default=""): str,
        }))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the Grocy calendar config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_set_day_plan(hass: HomeAssistant, data: dict) -> None:
    """Replace one day of rows owned by this integration."""
    client = next(iter(hass.data[DOMAIN].values()))[DATA_CLIENT]
    sections = await client.get("objects/meal_plan_sections")
    section_id = next((item["id"] for item in sections if item.get("name") == MEAL_PLAN_SECTION), None)
    if section_id is None:
        section_id = await client.post("objects/meal_plan_sections", {"name": MEAL_PLAN_SECTION, "sort_number": 100})
    existing = await client.get("objects/meal_plan")
    for item in existing:
        if item.get("day") == data["day"] and item.get("section_id") == section_id:
            await client.delete(f"objects/meal_plan/{item['id']}")
    if data["meal_type"] == "recipe":
        recipes = {item["name"].casefold(): item["id"] for item in await client.get("objects/recipes")}
        for name in (data["main_dish"], data["side_dish"]):
            if not name:
                continue
            recipe_id = recipes.get(name.casefold())
            if recipe_id is None:
                raise GrocyApiError(f"Grocy recipe {name!r} was not found")
            await client.post("objects/meal_plan", {"day": data["day"], "type": "recipe", "recipe_id": recipe_id, "section_id": section_id})
        for duty, assignee in (("Cooking", data["cooking_assignee"]), ("Dishes", data["dishes_assignee"])):
            if assignee:
                await client.post("objects/meal_plan", {"day": data["day"], "type": "note", "note": f"{duty}: {assignee}", "section_id": section_id})
    elif data["meal_type"] == "takeout":
        await client.post("objects/meal_plan", {"day": data["day"], "type": "note", "note": f"Takeout: {data['main_dish'] or 'TBD'}", "section_id": section_id})
    else:
        await client.post("objects/meal_plan", {"day": data["day"], "type": "note", "note": "KYO", "section_id": section_id})
