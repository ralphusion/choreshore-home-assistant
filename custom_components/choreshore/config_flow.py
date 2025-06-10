
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
    """Validate the user input by calling the ha-analytics edge function."""
    session = async_get_clientsession(hass)
    
    # Use the existing ha-analytics edge function for validation
    url = f"{API_BASE_URL}/functions/v1/ha-analytics"
    payload = {"household_id": data[CONF_HOUSEHOLD_ID]}
    
    try:
        async with session.post(
            url, 
            headers=API_HEADERS, 
            json=payload,
            timeout=10
        ) as response:
            if response.status != 200:
                _LOGGER.error("Edge function validation failed with status: %s", response.status)
                raise InvalidAuth
            
            result = await response.json()
            
            # Check if the response contains an error
            if "error" in result:
                _LOGGER.error("Edge function returned error: %s", result["error"])
                raise InvalidAuth
            
            # Validate that we got meaningful data back
            members = result.get("members", [])
            if not members:
                _LOGGER.error("No household members found")
                raise InvalidHousehold
            
            # Check if the provided user_id is in the household members
            user_found = False
            user_name = "User"
            for member in members:
                if member.get("id") == data[CONF_USER_ID]:
                    user_found = True
                    user_name = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip() or "User"
                    break
            
            if not user_found:
                _LOGGER.error("User ID %s not found in household members", data[CONF_USER_ID])
                raise InvalidAuth
                
    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to ChoreShore: %s", err)
        raise CannotConnect from err

    return {"title": f"ChoreShore - {user_name}"}

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
