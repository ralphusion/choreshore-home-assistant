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
        
        update_interval = timedelta(
            seconds=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from ChoreShore API."""
        try:
            _LOGGER.debug("Starting data fetch for household: %s", self.household_id)
            
            # Fetch data sources separately for better error handling
            chore_instances = await self._fetch_chore_instances()
            members = await self._fetch_household_members()

            _LOGGER.info("Fetched %d chore instances and %d members", 
                        len(chore_instances or []), len(members or []))

            # Log sample data for debugging
            if chore_instances:
                _LOGGER.info("Sample chore instance: %s", chore_instances[0])

            # Calculate analytics from the fetched data
            analytics = self._calculate_analytics(chore_instances or [])
            _LOGGER.info("Calculated analytics: %s", analytics)

            return {
                "chore_instances": chore_instances or [],
                "analytics": analytics,
                "members": members or [],
                "last_updated": datetime.now(),
            }

        except Exception as err:
            _LOGGER.error("Error updating ChoreShore data: %s", err, exc_info=True)
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def _fetch_chore_instances(self) -> List[Dict[str, Any]]:
        """Fetch chore instances from the API using simpler queries."""
        try:
            # First, get chore instances for the household
            instances_url = f"{API_BASE_URL}/rest/v1/chore_instances"
            instances_params = {
                "select": "*",
                "order": "due_date.asc"
            }

            _LOGGER.debug("Fetching chore instances from: %s", instances_url)

            async with self.session.get(
                instances_url, headers=API_HEADERS, params=instances_params, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Error fetching chore instances: %s - %s", response.status, error_text)
                    return []
                
                instances = await response.json()
                _LOGGER.info("Fetched %d total chore instances", len(instances))

            if not instances:
                return []

            # Get chore IDs to filter by household
            chore_ids = list(set(instance.get("chore_id") for instance in instances if instance.get("chore_id")))
            
            if not chore_ids:
                return []

            # Get chores for this household
            chores_url = f"{API_BASE_URL}/rest/v1/chores"
            chores_params = {
                "select": "id,name,household_id,category,priority,description,location,estimated_duration,instructions,frequency_type,frequency_config",
                "household_id": f"eq.{self.household_id}"
            }

            async with self.session.get(
                chores_url, headers=API_HEADERS, params=chores_params, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Error fetching chores: %s - %s", response.status, error_text)
                    return []
                
                chores = await response.json()
                _LOGGER.info("Fetched %d chores for household", len(chores))

            # Create lookup for chores
            chores_lookup = {chore["id"]: chore for chore in chores}
            
            # Filter instances to only include those from our household chores
            household_instances = []
            for instance in instances:
                chore_id = instance.get("chore_id")
                if chore_id in chores_lookup:
                    # Add chore details to instance
                    instance["chores"] = chores_lookup[chore_id]
                    household_instances.append(instance)

            _LOGGER.info("Filtered to %d household chore instances", len(household_instances))
            
            # Get user profiles for assigned users
            if household_instances:
                user_ids = list(set(instance.get("assigned_to") for instance in household_instances if instance.get("assigned_to")))
                
                if user_ids:
                    profiles_url = f"{API_BASE_URL}/rest/v1/profiles"
                    profiles_params = {
                        "select": "id,first_name,last_name",
                        "id": f"in.({','.join(user_ids)})"
                    }

                    async with self.session.get(
                        profiles_url, headers=API_HEADERS, params=profiles_params, timeout=DEFAULT_TIMEOUT
                    ) as response:
                        if response.status == 200:
                            profiles = await response.json()
                            profiles_lookup = {profile["id"]: profile for profile in profiles}
                            
                            # Add user details to instances
                            for instance in household_instances:
                                assigned_to = instance.get("assigned_to")
                                if assigned_to in profiles_lookup:
                                    instance["assigned_user"] = profiles_lookup[assigned_to]
                                
                                completed_by = instance.get("completed_by")
                                if completed_by in profiles_lookup:
                                    instance["completed_user"] = profiles_lookup[completed_by]

            return household_instances

        except Exception as err:
            _LOGGER.error("Exception fetching chore instances: %s", err, exc_info=True)
            return []

    async def _fetch_household_members(self) -> List[Dict[str, Any]]:
        """Fetch household members."""
        url = f"{API_BASE_URL}/rest/v1/profiles"
        params = {
            "household_id": f"eq.{self.household_id}",
            "select": "id,first_name,last_name,role,avatar_url",
        }

        _LOGGER.debug("Fetching household members with params: %s", params)

        try:
            async with self.session.get(
                url, headers=API_HEADERS, params=params, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.info("Successfully fetched %d household members", len(data))
                    return data
                else:
                    error_text = await response.text()
                    _LOGGER.error("Error fetching household members: %s - %s", response.status, error_text)
                    return []
        except Exception as err:
            _LOGGER.error("Exception fetching household members: %s", err, exc_info=True)
            return []

    def _calculate_analytics(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate analytics from chore instances."""
        if not instances:
            _LOGGER.info("No instances to calculate analytics from")
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
        _LOGGER.info("Calculating analytics for %d instances, today is %s", total_tasks, today)

        for task in instances:
            status = task.get("status", "")
            due_date = task.get("due_date", "")
            
            _LOGGER.debug("Processing task: status=%s, due_date=%s", status, due_date)
            
            if status == "completed":
                completed_tasks += 1
            elif status == "pending":
                pending_tasks += 1
                # Check if task is overdue
                if due_date:
                    try:
                        # Parse the due_date - it should be in YYYY-MM-DD format
                        if isinstance(due_date, str):
                            task_due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                        else:
                            task_due_date = due_date
                        
                        if task_due_date < today:
                            overdue_tasks += 1
                            _LOGGER.debug("Task is overdue: due=%s, today=%s", task_due_date, today)
                    except (ValueError, AttributeError) as e:
                        _LOGGER.warning("Could not parse due_date '%s': %s", due_date, e)
        
        completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        
        analytics = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": completion_rate,
        }
        
        _LOGGER.info("Final analytics: %s", analytics)
        return analytics

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
