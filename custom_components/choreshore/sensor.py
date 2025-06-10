
"""ChoreShore sensor platform."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TASK_STATUS_PENDING
from .coordinator import ChoreShoreDateUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreShore sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Analytics sensors (household-level)
    entities.extend([
        ChoreShoreTotalTasksSensor(coordinator),
        ChoreShoreCompletedTasksSensor(coordinator),
        ChoreShoreOverdueTasksSensor(coordinator),
        ChoreShorePendingTasksSensor(coordinator),
        ChoreShoreCompletionRateSensor(coordinator),
    ])
    
    # Chore status sensors (one per unique chore with pending instances)
    if coordinator.data and "chore_instances" in coordinator.data:
        chore_groups = {}
        
        # Group pending instances by chore_id
        for task in coordinator.data["chore_instances"]:
            if task.get("status") == TASK_STATUS_PENDING:
                chore_id = task.get("chores", {}).get("id")
                if chore_id:
                    if chore_id not in chore_groups:
                        chore_groups[chore_id] = []
                    chore_groups[chore_id].append(task)
        
        # Create one sensor per chore group
        for chore_id, instances in chore_groups.items():
            if instances:  # Only create sensor if there are pending instances
                entities.append(ChoreShoreChoreStatusSensor(coordinator, chore_id, instances))
    
    _LOGGER.info("Setting up %d ChoreShore sensor entities", len(entities))
    async_add_entities(entities)

class ChoreShoreBaseSensor(CoordinatorEntity, SensorEntity):
    """Base ChoreShore sensor."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.household_id)},
            "name": "ChoreShore Household",
            "manufacturer": "ChoreShore",
            "model": "Household Management",
        }

class ChoreShoreTotalTasksSensor(ChoreShoreBaseSensor):
    """Total tasks sensor."""

    _attr_name = "ChoreShore Total Tasks"
    _attr_unique_id = f"{DOMAIN}_total_tasks"
    _attr_icon = "mdi:format-list-checks"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("total_tasks", 0)
        _LOGGER.debug("Total tasks sensor returning: %s", value)
        return value

class ChoreShoreCompletedTasksSensor(ChoreShoreBaseSensor):
    """Completed tasks sensor."""

    _attr_name = "ChoreShore Completed Tasks"
    _attr_unique_id = f"{DOMAIN}_completed_tasks"
    _attr_icon = "mdi:check-circle"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("completed_tasks", 0)
        _LOGGER.debug("Completed tasks sensor returning: %s", value)
        return value

class ChoreShoreOverdueTasksSensor(ChoreShoreBaseSensor):
    """Overdue tasks sensor."""

    _attr_name = "ChoreShore Overdue Tasks"
    _attr_unique_id = f"{DOMAIN}_overdue_tasks"
    _attr_icon = "mdi:alert-circle"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("overdue_tasks", 0)
        _LOGGER.debug("Overdue tasks sensor returning: %s", value)
        return value

class ChoreShorePendingTasksSensor(ChoreShoreBaseSensor):
    """Pending tasks sensor."""

    _attr_name = "ChoreShore Pending Tasks"
    _attr_unique_id = f"{DOMAIN}_pending_tasks"
    _attr_icon = "mdi:clock-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("pending_tasks", 0)
        _LOGGER.debug("Pending tasks sensor returning: %s", value)
        return value

class ChoreShoreCompletionRateSensor(ChoreShoreBaseSensor):
    """Completion rate sensor."""

    _attr_name = "ChoreShore Completion Rate"
    _attr_unique_id = f"{DOMAIN}_completion_rate"
    _attr_icon = "mdi:percent"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("completion_rate", 0)
        _LOGGER.debug("Completion rate sensor returning: %s", value)
        return value

class ChoreShoreChoreStatusSensor(ChoreShoreBaseSensor):
    """Chore status sensor (one per unique chore)."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator, chore_id: str, instances: List[Dict[str, Any]]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._chore_id = chore_id
        self._instances = instances
        
        # Use the first instance to get chore details
        first_instance = instances[0] if instances else {}
        chore_data = first_instance.get("chores", {})
        self._chore_name = chore_data.get("name", "Unknown Chore")

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._chore_name} Tasks"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{DOMAIN}_chore_{self._chore_id}_status"

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:clipboard-list"

    @property
    def state_class(self) -> str:
        """Return the state class."""
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the number of pending instances for this chore."""
        current_instances = self._get_current_instances()
        count = len(current_instances)
        _LOGGER.debug("Chore %s has %d pending instances", self._chore_name, count)
        return count

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return len(self._get_current_instances()) > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        current_instances = self._get_current_instances()
        if not current_instances:
            return {"chore_name": self._chore_name, "pending_instances": 0}

        # Get chore details from first instance
        first_instance = current_instances[0]
        chore = first_instance.get("chores", {})
        
        # Find earliest and most overdue dates
        earliest_due = None
        most_overdue = None
        today = datetime.now().date()
        
        # Get unique assigned members
        assigned_members = set()
        overdue_count = 0
        
        for instance in current_instances:
            # Assigned members
            assigned_user = instance.get("assigned_user", {})
            if assigned_user:
                member_name = f"{assigned_user.get('first_name', '')} {assigned_user.get('last_name', '')}".strip()
                if member_name:
                    assigned_members.add(member_name)
            
            # Due dates
            due_date_str = instance.get("due_date")
            if due_date_str:
                try:
                    if isinstance(due_date_str, str):
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    else:
                        due_date = due_date_str
                    
                    # Track earliest due date
                    if earliest_due is None or due_date < earliest_due:
                        earliest_due = due_date
                    
                    # Track overdue
                    if due_date < today:
                        overdue_count += 1
                        if most_overdue is None or due_date < most_overdue:
                            most_overdue = due_date
                            
                except (ValueError, AttributeError):
                    pass
        
        return {
            "chore_name": self._chore_name,
            "chore_id": self._chore_id,
            "pending_instances": len(current_instances),
            "overdue_instances": overdue_count,
            "assigned_members": list(assigned_members),
            "next_due_date": earliest_due.isoformat() if earliest_due else None,
            "most_overdue_date": most_overdue.isoformat() if most_overdue else None,
            "category": chore.get("category"),
            "priority": chore.get("priority"),
            "location": chore.get("location"),
            "description": chore.get("description"),
            "estimated_duration": chore.get("estimated_duration"),
        }

    def _get_current_instances(self) -> List[Dict[str, Any]]:
        """Get current pending instances for this chore from coordinator data."""
        if not self.coordinator.data or "chore_instances" not in self.coordinator.data:
            return []
        
        current_instances = []
        for task in self.coordinator.data["chore_instances"]:
            chore_data = task.get("chores", {})
            if (chore_data.get("id") == self._chore_id and 
                task.get("status") == TASK_STATUS_PENDING):
                current_instances.append(task)
        
        return current_instances
