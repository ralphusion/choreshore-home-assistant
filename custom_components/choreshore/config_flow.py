
"""Config flow for ChoreShore integration."""
import logging
from typing import Any, Dict, Optional

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_URL, CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_HOUSEHOLD_ID,
    CONF_USER_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    API_BASE_URL,
    API_HEADERS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOUSEHOLD_ID): str,
    vol.Required(CONF_USER_ID): str,
    vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
})

async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    
    # Test connection by fetching user profile directly from profiles table
    url = f"{API_BASE_URL}/rest/v1/profiles"
    params = {
        "select": "*",
        "id": f"eq.{data[CONF_USER_ID]}"
    }
    
    try:
        async with session.get(
            url, headers=API_HEADERS, params=params, timeout=10
        ) as response:
            if response.status != 200:
                raise InvalidAuth
            
            profile_data = await response.json()
            if not profile_data or len(profile_data) == 0:
                raise InvalidAuth
                
            profile = profile_data[0]
            if profile.get("household_id") != data[CONF_HOUSEHOLD_ID]:
                raise InvalidHousehold
                
    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to ChoreShore: %s", err)
        raise CannotConnect from err

    return {"title": f"ChoreShore - {profile.get('first_name', 'User')}"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ChoreShore."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidHousehold:
                errors["base"] = "invalid_household"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidHousehold(HomeAssistantError):
    """Error to indicate invalid household."""
