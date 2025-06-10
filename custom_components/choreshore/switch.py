
"""ChoreShore switch platform."""
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TASK_STATUS_PENDING, TASK_STATUS_COMPLETED
from .coordinator import ChoreShoreDateUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreShore switch platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Group pending tasks by chore for this specific user
    if coordinator.data and "chore_instances" in coordinator.data:
        chore_groups = {}
        
        # Group instances by chore_id (already filtered to this user's tasks)
        for task in coordinator.data["chore_instances"]:
            if task.get("status") == TASK_STATUS_PENDING:
                chore_id = task.get("chores", {}).get("id")
                if chore_id:
                    if chore_id not in chore_groups:
                        chore_groups[chore_id] = []
                    chore_groups[chore_id].append(task)
        
        # Create one switch per chore group for this user
        for chore_id, instances in chore_groups.items():
            if instances:  # Only create switch if there are pending instances
                entities.append(ChoreShoreUserChoreSwitch(coordinator, chore_id, instances))
    
    _LOGGER.info("Setting up %d ChoreShore chore switches for user %s", 
                len(entities), coordinator.user_id)
    async_add_entities(entities)

class ChoreShoreUserChoreSwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for ChoreShore chores (user-specific, grouped by chore type)."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator, chore_id: str, instances: List[Dict[str, Any]]) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._chore_id = chore_id
        self._instances = instances
        
        # Use the first instance to get chore details
        first_instance = instances[0] if instances else {}
        chore_data = first_instance.get("chores", {})
        self._chore_name = chore_data.get("name", "Unknown Chore")
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.household_id}_{coordinator.user_id}")},
            "name": f"ChoreShore - {coordinator.user_name}",
            "manufacturer": "ChoreShore",
            "model": "User Tasks",
        }

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self.coordinator.user_name} {self._chore_name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the switch."""
        return f"{DOMAIN}_{self.coordinator.user_id}_chore_{self._chore_id}"

    @property
    def icon(self) -> str:
        """Return the icon of the switch."""
        return "mdi:check-circle" if self.is_on else "mdi:circle-outline"

    @property
    def is_on(self) -> bool:
        """Return true if any instance of this chore is completed (switch represents completion action)."""
        # Switch is "off" when there are pending instances (ready to complete)
        # Switch is "on" momentarily during completion, then refreshes to off if more instances exist
        current_instances = self._get_current_instances()
        return len(current_instances) == 0  # No pending instances = all completed

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        current_instances = self._get_current_instances()
        return len(current_instances) > 0  # Available if there are pending instances

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        current_instances = self._get_current_instances()
        if not current_instances:
            return {
                "chore_name": self._chore_name, 
                "pending_instances": 0,
                "user_id": self.coordinator.user_id,
                "user_name": self.coordinator.user_name,
            }

        # Get chore details from first instance
        first_instance = current_instances[0]
        chore = first_instance.get("chores", {})
        
        # Find most overdue instance
        most_overdue = self._get_most_overdue_instance(current_instances)
        most_overdue_date = most_overdue.get("due_date") if most_overdue else None
        
        # Count overdue instances
        overdue_count = 0
        today = datetime.now().date()
        for instance in current_instances:
            if instance.get("due_date"):
                try:
                    due_date_str = instance.get("due_date", "")
                    if isinstance(due_date_str, str):
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    else:
                        due_date = due_date_str
                    
                    if due_date < today:
                        overdue_count += 1
                except (ValueError, AttributeError):
                    pass
        
        return {
            "chore_name": self._chore_name,
            "chore_id": self._chore_id,
            "user_id": self.coordinator.user_id,
            "user_name": self.coordinator.user_name,
            "pending_instances": len(current_instances),
            "overdue_instances": overdue_count,
            "most_overdue_date": most_overdue_date,
            "category": chore.get("category"),
            "priority": chore.get("priority"),
            "location": chore.get("location"),
            "description": chore.get("description"),
            "estimated_duration": chore.get("estimated_duration"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Complete the most overdue instance of this chore for this user."""
        current_instances = self._get_current_instances()
        if not current_instances:
            _LOGGER.warning("No pending instances found for chore %s for user %s", 
                          self._chore_name, self.coordinator.user_id)
            return
        
        # Find the most overdue instance
        most_overdue = self._get_most_overdue_instance(current_instances)
        if not most_overdue:
            _LOGGER.warning("Could not determine most overdue instance for chore %s for user %s", 
                          self._chore_name, self.coordinator.user_id)
            return
        
        task_id = most_overdue["id"]
        _LOGGER.info("Completing most overdue instance %s for chore %s for user %s", 
                    task_id, self._chore_name, self.coordinator.user_id)
        
        success = await self.coordinator.complete_task(task_id)
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to complete task %s for chore %s for user %s", 
                         task_id, self._chore_name, self.coordinator.user_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (not supported for chore completion)."""
        _LOGGER.warning("Cannot uncomplete a chore via switch")

    def _get_current_instances(self) -> List[Dict[str, Any]]:
        """Get current pending instances for this chore assigned to this user from coordinator data."""
        if not self.coordinator.data or "chore_instances" not in self.coordinator.data:
            return []
        
        current_instances = []
        for task in self.coordinator.data["chore_instances"]:
            chore_data = task.get("chores", {})
            if (chore_data.get("id") == self._chore_id and 
                task.get("status") == TASK_STATUS_PENDING and
                task.get("assigned_to") == self.coordinator.user_id):
                current_instances.append(task)
        
        return current_instances

    def _get_most_overdue_instance(self, instances: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the most overdue instance from a list of instances."""
        if not instances:
            return None
        
        today = datetime.now().date()
        overdue_instances = []
        future_instances = []
        
        for instance in instances:
            due_date_str = instance.get("due_date")
            if not due_date_str:
                future_instances.append(instance)
                continue
                
            try:
                if isinstance(due_date_str, str):
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                else:
                    due_date = due_date_str
                
                if due_date < today:
                    overdue_instances.append((instance, due_date))
                else:
                    future_instances.append((instance, due_date))
            except (ValueError, AttributeError):
                future_instances.append(instance)
        
        # Return most overdue instance (earliest due date)
        if overdue_instances:
            overdue_instances.sort(key=lambda x: x[1])
            return overdue_instances[0][0]
        
        # If no overdue, return earliest future instance
        if future_instances:
            # Handle instances without dates
            with_dates = [(inst, date) for inst, date in future_instances if not isinstance(inst, dict)]
            without_dates = [inst for inst in future_instances if isinstance(inst, dict)]
            
            if with_dates:
                with_dates.sort(key=lambda x: x[1])
                return with_dates[0][0]
            elif without_dates:
                return without_dates[0]
        
        # Fallback to first instance
        return instances[0]
