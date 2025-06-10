
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
            "name": coordinator.device_name,
            "manufacturer": "ChoreShore",
            "model": "User Tasks",
        }

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self.coordinator.device_name} {self._chore_name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the switch."""
        return f"{DOMAIN}_{self.coordinator.user_id}_chore_{self._chore_id}"

    # ... keep existing code (icon, is_on, available, extra_state_attributes, async_turn_on, async_turn_off, _get_current_instances, _get_most_overdue_instance methods)
