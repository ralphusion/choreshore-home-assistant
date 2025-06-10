
"""ChoreShore binary sensor platform."""
import logging
from typing import Any, Dict

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ChoreShoreDateUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreShore binary sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create user-specific binary sensors
    entities = [
        ChoreShoreOverdueTasksBinarySensor(coordinator),
        ChoreShorePendingTasksBinarySensor(coordinator),
    ]
    
    _LOGGER.info("Setting up %d ChoreShore binary sensor entities for user %s", 
                len(entities), coordinator.user_id)
    async_add_entities(entities)

class ChoreShoreBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base ChoreShore binary sensor."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.household_id}_{coordinator.user_id}")},
            "name": coordinator.device_name,
            "manufacturer": "ChoreShore",
            "model": "User Tasks",
        }

class ChoreShoreOverdueTasksBinarySensor(ChoreShoreBaseBinarySensor):
    """Binary sensor for user's overdue tasks."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Has Overdue Tasks"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.user_id}_has_overdue_tasks"
        self._attr_icon = "mdi:alert-circle"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    # ... keep existing code (is_on and extra_state_attributes properties)

class ChoreShorePendingTasksBinarySensor(ChoreShoreBaseBinarySensor):
    """Binary sensor for user's pending tasks."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Has Pending Tasks"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.user_id}_has_pending_tasks"
        self._attr_icon = "mdi:clock-outline"

    # ... keep existing code (is_on and extra_state_attributes properties)
