
"""Data update coordinator for ChoreShore."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_HOUSEHOLD_ID,
    CONF_USER_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TIMEOUT,
    API_BASE_URL,
    API_HEADERS,
)

_LOGGER = logging.getLogger(__name__)

class ChoreShoreDateUpdateCoordinator(DataUpdateCoordinator):
    """ChoreShore data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.household_id = entry.data[CONF_HOUSEHOLD_ID]
        self.user_id = entry.data[CONF_USER_ID]
        self.session = async_get_clientsession(hass)
        
        # Get user profile information for device naming
        self._user_name = None
        
        update_interval = timedelta(
            seconds=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.user_id}",
            update_interval=update_interval,
        )

    @property
    def user_name(self) -> str:
        """Get the user's display name."""
        if self._user_name is None:
            # Try to get user name from coordinator data
            if self.data and "members" in self.data:
                for member in self.data["members"]:
                    if member.get("id") == self.user_id:
                        first_name = member.get("first_name", "")
                        last_name = member.get("last_name", "")
                        self._user_name = f"{first_name} {last_name}".strip() or "User"
                        break
            
            if self._user_name is None:
                self._user_name = f"User {self.user_id[:8]}"
        
        return self._user_name

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from ChoreShore API via dedicated edge function."""
        try:
            _LOGGER.info("Fetching data via edge function for household: %s, user: %s", 
                        self.household_id, self.user_id)
            
            # Call the dedicated edge function
            url = f"{API_BASE_URL}/functions/v1/ha-analytics"
            data = {"household_id": self.household_id}
            
            async with self.session.post(
                url, 
                headers=API_HEADERS, 
                json=data, 
                timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Edge function error: %s - %s", response.status, error_text)
                    raise UpdateFailed(f"Edge function error: {response.status}")
                
                result = await response.json()
                
                if "error" in result:
                    _LOGGER.error("Edge function returned error: %s", result["error"])
                    raise UpdateFailed(f"Edge function error: {result['error']}")
                
                # Filter data to be user-specific
                filtered_result = self._filter_user_data(result)
                
                # Log the results
                analytics = filtered_result.get("analytics", {})
                instances = filtered_result.get("chore_instances", [])
                members = filtered_result.get("members", [])
                
                _LOGGER.info("Successfully fetched filtered data for user %s: %d instances, %d members", 
                           self.user_id, len(instances), len(members))
                _LOGGER.info("User-specific analytics: %s", analytics)
                
                return filtered_result

        except Exception as err:
            _LOGGER.error("Error updating ChoreShore data: %s", err, exc_info=True)
            raise UpdateFailed(f"Error updating data: {err}") from err

    def _filter_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter the data to show only user-relevant information."""
        if not data:
            return data
        
        # Filter chore instances to only show tasks assigned to this user
        user_instances = []
        all_instances = data.get("chore_instances", [])
        
        for instance in all_instances:
            if instance.get("assigned_to") == self.user_id:
                user_instances.append(instance)
        
        # Recalculate analytics based on user's tasks only
        user_analytics = self._calculate_user_analytics(user_instances)
        
        # Keep all members info for reference but filter instances
        filtered_data = {
            "chore_instances": user_instances,
            "members": data.get("members", []),
            "analytics": user_analytics,
            "last_updated": data.get("last_updated"),
        }
        
        return filtered_data

    def _calculate_user_analytics(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate analytics for user-specific instances."""
        if not instances:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "overdue_tasks": 0,
                "pending_tasks": 0,
                "completion_rate": 0,
            }

        total_tasks = len(instances)
        completed_tasks = 0
        overdue_tasks = 0
        pending_tasks = 0
        
        today = datetime.now().date()
        
        for task in instances:
            status = task.get("status", "")
            due_date_str = task.get("due_date")
            
            if status == "completed":
                completed_tasks += 1
            elif status == "pending":
                pending_tasks += 1
                
                # Check if overdue
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                        if due_date < today:
                            overdue_tasks += 1
                    except (ValueError, TypeError):
                        pass
        
        completion_rate = round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": completion_rate,
        }

    async def complete_task(self, task_id: str) -> bool:
        """Complete a task via the API."""
        try:
            url = f"{API_BASE_URL}/rest/v1/rpc/complete_shared_chore_instances"
            data = {
                "p_instance_id": task_id,
                "p_completed_by": self.user_id,
            }

            _LOGGER.debug("Completing task %s for user %s", task_id, self.user_id)

            async with self.session.post(
                url, headers=API_HEADERS, json=data, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully completed task %s", task_id)
                    await self.async_request_refresh()
                    return True
                else:
                    error_text = await response.text()
                    _LOGGER.error("Error completing task %s: %s - %s", task_id, response.status, error_text)
                    return False

        except Exception as err:
            _LOGGER.error("Error completing task %s: %s", task_id, err)
            return False

    async def skip_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Skip a task via the API."""
        try:
            url = f"{API_BASE_URL}/rest/v1/rpc/skip_shared_chore_instances"
            data = {
                "p_instance_id": task_id,
                "p_skipped_by": self.user_id,
                "p_skip_reason": reason,
            }

            _LOGGER.debug("Skipping task %s for user %s with reason: %s", task_id, self.user_id, reason)

            async with self.session.post(
                url, headers=API_HEADERS, json=data, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully skipped task %s", task_id)
                    await self.async_request_refresh()
                    return True
                else:
                    error_text = await response.text()
                    _LOGGER.error("Error skipping task %s: %s - %s", task_id, response.status, error_text)
                    return False

        except Exception as err:
            _LOGGER.error("Error skipping task %s: %s", task_id, err)
            return False
