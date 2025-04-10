# custom_components/sunway_fve/number.py
import logging
import math
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian

from .const import DOMAIN, RW_REGISTER_MAP
from . import SunwayFveCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Sunway FVE number entities."""
    coordinator: SunwayFveCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for key, params in RW_REGISTER_MAP.items():
        if params.get("type") == "number":
            entities.append(SunwayModbusNumber(coordinator, key, params))
            _LOGGER.debug(f"Setting up number: {key}")

    async_add_entities(entities)

class SunwayModbusNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Sunway FVE Modbus number."""

    def __init__(self, coordinator: SunwayFveCoordinator, key: str, params: dict):
        """Initialize the number."""
        super().__init__(coordinator)
        self._key = key
        self._params = params
        self._attr_name = f"Sunway {key.replace('_', ' ').title()}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.host}_{key}"
        self._attr_native_unit_of_measurement = params.get("unit")
        self._attr_native_min_value = params.get("min_value", 0) # Výchozí min
        self._attr_native_max_value = params.get("max_value", 65535) # Výchozí max pro U16
        self._attr_native_step = params.get("step", 1)
        self._attr_mode = NumberMode(params.get("mode", "auto")) # "auto", "slider", "box"
        self._data_type = params.get("data_type", "U16") # Důležité pro zápis
        self._register_count = params.get("count", 1) # Důležité pro zápis
        self._scale = params.get("scale", 1.0) # Důležité pro zápis

        # Device Info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host, coordinator.slave_id)},
            # Další info jako v sensor.py
        }

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Hodnota se čte z coordinatora (už by měla být škálovaná)
        val = self.coordinator.data.get(self._key)
        if val is None:
            return None
        # Ověření, zda je hodnota číslo
        if isinstance(val, (int, float)):
            return float(val)
        _LOGGER.warning(f"Received non-numeric value '{val}' for number entity {self.name}")
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        address = self._params["address"]

        # Převedení float hodnoty zpět na integer pro Modbus s ohledem na scale
        raw_value: int
        if self._scale != 1.0:
            if self._scale > 1:
                raw_value = int(round(value * self._scale))
            else: # scale < 1
                raw_value = int(round(value / self._scale)) # Dělení scale (např. value / 0.1)
        else:
            raw_value = int(round(value))

        _LOGGER.debug(f"Setting number {self.name} to {value} (Raw: {raw_value}, Register: {address}, Type: {self._data_type}, Count: {self._register_count})")

        # Zápis do Modbus registru(ů)
        success = False
        if self._register_count == 1:
             if self._data_type == "U16":
                 # Zajistit, aby hodnota byla v rozsahu U16 (0-65535)
                 if 0 <= raw_value <= 65535:
                     success = await self.coordinator.async_write_register(address, raw_value)
                 else:
                     _LOGGER.error(f"Value {raw_value} out of range for U16 register {address}")
             elif self._data_type == "I16":
                  # Zajistit, aby hodnota byla v rozsahu I16 (-32768 až 32767)
                 if -32768 <= raw_value <= 32767:
                     success = await self.coordinator.async_write_register(address, raw_value)
                 else:
                      _LOGGER.error(f"Value {raw_value} out of range for I16 register {address}")
             else:
                 _LOGGER.error(f"Unsupported data type {self._data_type} for single register write on {self.name}")
        elif self._register_count == 2:
             # Potřeba BinaryPayloadBuilder pro 32bit hodnoty
             builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
             if self._data_type == "U32":
                 builder.add_32bit_uint(raw_value)
             elif self._data_type == "I32":
                 builder.add_32bit_int(raw_value)
             # Přidejte další 32bit typy, pokud je potřeba
             else:
                 _LOGGER.error(f"Unsupported data type {self._data_type} for double register write on {self.name}")
                 return # Ukončit, pokud typ není podporován

             if builder.payload: # Pokud builder něco obsahuje
                registers_to_write = builder.to_registers()
                success = await self.coordinator.async_write_multiple_registers(address, registers_to_write)
        else:
            _LOGGER.error(f"Unsupported register count {self._register_count} for number entity {self.name}")


        if not success:
            _LOGGER.error(f"Failed to set number {self.name} to {value}")