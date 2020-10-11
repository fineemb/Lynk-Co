"""Support for the Colorfulclouds service."""
import logging
import string
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_DEVICE_CLASS,
    CONF_NAME,
    DEVICE_CLASS_TEMPERATURE,
)
from homeassistant.helpers.entity import Entity

from .const import (
    ATTR_ICON,
    ATTR_LABEL,
    ATTR_VEHICLE_STATUS,
    ATTR_ADD_VEHICLE_STATUS,
    ATTR_FRIENDLY_NAME,
    COORDINATOR,
    DOMAIN,
    NAME,
    OPTIONAL_SENSORS,
    BINARY_SENSOR_TYPES,
)

PARALLEL_UPDATES = 1
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add Colorfulclouds entities from a config_entry."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    binary_sensor = []
    for i in range(len(coordinator.data)):
        for sensor in BINARY_SENSOR_TYPES:
            binary_sensor.append(LynkCoBinarySensor(i, sensor, coordinator))
    async_add_entities(binary_sensor, False)


class LynkCoBinarySensor(BinarySensorEntity):
    """Define an Colorfulclouds entity."""

    def __init__(self, vin, kind, coordinator):
        """Initialize."""
        self._name = coordinator.data[vin]["plateNo"]
        self.kind = kind
        self.vin = vin
        self.coordinator = coordinator
        self._unique_id = coordinator.data[vin]["result"]['vin']
        self._device_class = None
        self._attrs = {"friendly_name_cn":BINARY_SENSOR_TYPES[self.kind][ATTR_FRIENDLY_NAME]}

    @property
    def name(self):
        """Return the name."""
        return BINARY_SENSOR_TYPES[self.kind][ATTR_LABEL]

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self._unique_id}-{self.kind}".lower()

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self._unique_id)},
            "name": self._name,
            "manufacturer": "Lynk&Co",
            "entry_type": "device",
            "model": self._name
        }

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def is_on(self):
        """Return the state."""
        state =  self.coordinator.data[self.vin]["vehicleStatus"][BINARY_SENSOR_TYPES[self.kind][ATTR_VEHICLE_STATUS]][BINARY_SENSOR_TYPES[self.kind][ATTR_ADD_VEHICLE_STATUS]][self.kind]
        if self.kind.find('seatBeltStatus') >=0:
            return state==False
        if self.kind.find('tyrePreWarning') >=0:
            return state==1
        if self.kind.find('LockStatus') >=0:
            return state==0
        return state

    @property
    def icon(self):
        """Return the icon."""
        icon = BINARY_SENSOR_TYPES[self.kind][ATTR_ICON]
        if self.kind == 'engineStatus':
            if self.coordinator.data[self.vin]["vehicleStatus"][BINARY_SENSOR_TYPES[self.kind][ATTR_VEHICLE_STATUS]][self.kind]=='ENGINE_OFF':
                icon = 'mdi:engine-off'
        if self.kind.find('winStatus') >=0:
            if self.coordinator.data[self.vin]["vehicleStatus"]['additionalVehicleStatus']['climateStatus'][self.kind]==0:
                icon = 'mdi:window-shutter-alert'
            elif self.coordinator.data[self.vin]["vehicleStatus"]['additionalVehicleStatus']['climateStatus'][self.kind]==1:
                icon = 'mdi:window-shutter-open'
        if self.kind == 'sunroofOpenStatus':
            if self.coordinator.data[self.vin]["vehicleStatus"]['additionalVehicleStatus']['climateStatus'][self.kind]==0:
                icon = 'mdi:window-open'
        return icon

    @property
    def device_class(self):
        """Return the device_class."""
        return BINARY_SENSOR_TYPES[self.kind][ATTR_DEVICE_CLASS]


    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        self._attrs["friendly_name"] = BINARY_SENSOR_TYPES[self.kind][ATTR_FRIENDLY_NAME]
        return self._attrs

    @property
    def entity_registry_enabled_default(self):
        """Return if the entity should be enabled when first added to the entity registry."""
        return bool(self.kind not in OPTIONAL_SENSORS)

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update Colorfulclouds entity."""
        # _LOGGER.debug("weather_update: %s", self.coordinator.data['server_time'])
        await self.coordinator.async_request_refresh()
