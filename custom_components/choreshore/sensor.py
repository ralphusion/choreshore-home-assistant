
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
    
    # User-specific analytics sensors
    entities.extend([
        ChoreShoreTotalTasksSensor(coordinator),
        ChoreShoreCompletedTasksSensor(coordinator),
        ChoreShoreOverdueTasksSensor(coordinator),
        ChoreShorePendingTasksSensor(coordinator),
        ChoreShoreCompletionRateSensor(coordinator),
    ])
    
    # User-specific chore sensors (one per unique chore assigned to this user)
    if coordinator.data and "chore_instances" in coordinator.data:
        unique_chores = {}
        
        # Group user's instances by chore_id to identify unique chores
        for task in coordinator.data["chore_instances"]:
            chore_data = task.get("chores", {})
            chore_id = chore_data.get("id")
            if chore_id and chore_id not in unique_chores:
                unique_chores[chore_id] = chore_data
        
        # Create one sensor per unique chore assigned to this user
        for chore_id, chore_data in unique_chores.items():
            entities.append(ChoreShoreUserChoreStatusSensor(coordinator, chore_id, chore_data))
    
    _LOGGER.info("Setting up %d ChoreShore sensor entities for user %s", 
                len(entities), coordinator.user_id)
    async_add_entities(entities)

class ChoreShoreBaseSensor(CoordinatorEntity, SensorEntity):
    """Base ChoreShore sensor."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.household_id}_{coordinator.user_id}")},
            "name": coordinator.device_name,
            "manufacturer": "ChoreShore",
            "model": "User Tasks",
        }

class ChoreShoreTotalTasksSensor(ChoreShoreBaseSensor):
    """Total tasks sensor for user."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Total Tasks"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.user_id}_total_tasks"
        self._attr_icon = "mdi:format-list-checks"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    # ... keep existing code (native_value property)

class ChoreShoreCompletedTasksSensor(ChoreShoreBaseSensor):
    """Completed tasks sensor for user."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Completed Tasks"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.user_id}_completed_tasks"
        self._attr_icon = "mdi:check-circle"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    # ... keep existing code (native_value property)

class ChoreShoreOverdueTasksSensor(ChoreShoreBaseSensor):
    """Overdue tasks sensor for user."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Overdue Tasks"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.user_id}_overdue_tasks"
        self._attr_icon = "mdi:alert-circle"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    # ... keep existing code (native_value property)

class ChoreShorePendingTasksSensor(ChoreShoreBaseSensor):
    """Pending tasks sensor for user."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Pending Tasks"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.user_id}_pending_tasks"
        self._attr_icon = "mdi:clock-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    # ... keep existing code (native_value property)

class ChoreShoreCompletionRateSensor(ChoreShoreBaseSensor):
    """Completion rate sensor for user."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Completion Rate"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.user_id}_completion_rate"
        self._attr_icon = "mdi:percent"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"

    # ... keep existing code (native_value property)

class ChoreShoreUserChoreStatusSensor(ChoreShoreBaseSensor):
    """User-specific chore status sensor (one per unique chore assigned to user)."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator, chore_id: str, chore_data: Dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._chore_id = chore_id
        self._chore_data = chore_data
        self._chore_name = chore_data.get("name", "Unknown Chore")

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.coordinator.device_name} {self._chore_name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{DOMAIN}_{self.coordinator.user_id}_chore_{self._chore_id}"

    # ... keep existing code (icon, state_class, native_value, available, extra_state_attributes, _get_user_instances methods)
