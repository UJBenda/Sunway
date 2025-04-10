# custom_components/sunway_fve/__init__.py

import asyncio
import logging
from datetime import timedelta

# Import pro ASYNCHRONNÍ Modbus komunikaci
from pymodbus.client import AsyncModbusTcpClient # Používáme Async klienta
from pymodbus.exceptions import ConnectionException, ModbusIOException
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian

# Importy z Home Assistant Core
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady

# Importy z naší integrace (.const)
from .const import (
    DOMAIN,
    SENSOR_DESCRIPTIONS,
    RW_REGISTER_MAP,
)

# Nastavení loggeru
_LOGGER = logging.getLogger(__name__)

# Platformy
PLATFORMS = ["sensor", "switch", "number"] # Upravte podle potřeby

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Nastaví Sunway FVE z konfiguračního záznamu."""
    hass.data.setdefault(DOMAIN, {})
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave_id = entry.data[CONF_SLAVE]
    scan_interval = timedelta(seconds=entry.data.get(CONF_SCAN_INTERVAL, 30))

    _LOGGER.info(f"Nastavuje se integrace Sunway FVE pro {host}:{port} (Slave ID: {slave_id}) s ASYNC klientem")

    coordinator = SunwayFveCoordinator(hass, host, port, slave_id, scan_interval, entry.entry_id)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.async_shutdown()
        raise

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    _LOGGER.info(f"Sunway FVE integrace pro {entry.title} byla úspěšně nastavena (async).")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Odstraní konfigurační záznam."""
    _LOGGER.info(f"Odebírám integraci Sunway FVE pro {entry.title} (async)")
    coordinator = hass.data[DOMAIN].get(entry.entry_id)

    if coordinator:
        await coordinator.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info(f"Sunway FVE integrace pro {entry.title} byla úspěšně odebrána (async).")

    return unload_ok

async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    _LOGGER.debug(f"Aktualizuji konfiguraci pro {entry.title} (async)")
    await hass.config_entries.async_reload(entry.entry_id)

# --- ASYNCHRONNÍ Coordinator Class ---
class SunwayFveCoordinator(DataUpdateCoordinator):
    """ASYNC Coordinator pro získávání dat ze Sunway FVE."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, slave_id: int, scan_interval: timedelta, entry_id: str):
        """Inicializace async coordinatora."""
        _LOGGER.debug(f"Initializing ASYNC SunwayFveCoordinator for {entry_id}")
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({entry_id})_async",
            update_interval=scan_interval,
        )
        self.hass = hass # Uložíme si hass pro pozdější použití v _read_registers
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.entry_id = entry_id
        # Zvýšíme timeout pro jistotu na 10s
        self._client = AsyncModbusTcpClient(host, port=port, timeout=10)
        self._lock = asyncio.Lock()
        _LOGGER.debug(f"ASYNC SunwayFveCoordinator initialization finished for {entry_id}")

    async def _ensure_connection(self) -> bool:
        """Zajistí, že klient je připojen (voláno z async metod)."""
        if not self._client.connected:
            _LOGGER.info(f"Async Modbus klient není připojen, pokouším se připojit k {self.host}:{self.port}")
            try:
                await self._client.connect()
                return self._client.connected
            except Exception as e:
                _LOGGER.warning(f"Selhalo připojení Async Modbus klienta: {e}", exc_info=True)
                return False
        return True

    async def async_shutdown(self) -> None:
        """Zavře Modbus spojení při ukončení."""
        _LOGGER.info("Async Coordinator shutdown - Zavírám Modbus spojení.")
        if self._client.connected:
             self._client.close()
        await super().async_shutdown()

    async def _read_registers(self, address: int, count: int, data_type: str, scale: float, read_func) -> any:
        """Pomocná ASYNC funkce pro čtení a dekódování registrů."""
        # read_func je nyní předána z _async_update_data
        try:
            _LOGGER.debug(
                f"Attempting ASYNC read: Func={read_func.__name__}, Address={address}, Count={count}, SlaveID={self.slave_id}"
            )
            # Používáme explicitní pojmenování argumentů
            result = await read_func(address=address, count=count, slave=self.slave_id)

            if result.isError():
                _LOGGER.warning(f"Async Modbus read error for address {address}: {result}")
                return None
            else:
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(f"Async Modbus read successful for address {address}, Raw Registers: {result.registers}")

            decoder = BinaryPayloadDecoder.fromRegisters(
                result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG
            )
            raw_value = None
            if data_type == "U16": raw_value = decoder.decode_16bit_uint()
            elif data_type == "I16": raw_value = decoder.decode_16bit_int()
            elif data_type == "U32": raw_value = decoder.decode_32bit_uint()
            elif data_type == "I32": raw_value = decoder.decode_32bit_int()
            elif data_type == "STR":
                 string_length = count * 2
                 raw_value = decoder.decode_string(string_length).rstrip(b'\x00').decode('utf-8', errors='ignore')
            else:
                _LOGGER.warning(f"Neznámý datový typ '{data_type}' pro adresu {address}")
                return None

            if raw_value is not None and data_type != "STR":
                 if scale != 1.0:
                     try:
                         scaled_value = float(raw_value)
                         if scale > 1: return scaled_value / scale
                         elif scale < 1 and scale != 0: return scaled_value * scale
                         else: return scaled_value
                     except (ValueError, TypeError) as e:
                         _LOGGER.error(f"Chyba při ASYNC scale {scale} na {raw_value} pro adresu {address}: {e}")
                         return None
                 else: return raw_value
            elif raw_value is not None and data_type == "STR": return raw_value
            else: return None

        except ModbusIOException as e:
             _LOGGER.warning(f"Async Modbus IO chyba při čtení registru {address}: {e}")
             return None
        except ConnectionException as e:
            _LOGGER.warning(f"Async Modbus Connection chyba při čtení registru {address}: {e}")
            if self._client.connected: self._client.close()
            return None
        except Exception as e:
            _LOGGER.error(f"Neočekávaná chyba v ASYNC _read_registers pro adresu {address}: {e}", exc_info=True)
            return None

    async def _async_update_data(self):
        """ASYNCHRONNÍ získávání dat ze zařízení."""
        data = {}
        async with self._lock:
            try:
                is_connected = await self._ensure_connection()
                if not is_connected:
                    raise UpdateFailed(f"Nepodařilo se připojit k {self.host}:{self.port}")

                _LOGGER.debug(f"Zahajuji ASYNC čtení dat pro {self.name}")
                start_time = asyncio.get_event_loop().time()

                # V této verzi NEROZLIŠUJEME holding/input, čteme vše jako holding
                read_func_to_use = self._client.read_holding_registers

                tasks = []
                valid_sensor_descriptions = []
                # Smyčka pro senzory
                for desc in SENSOR_DESCRIPTIONS:
                     # Použijeme vždy stejnou funkci (v této verzi)
                     tasks.append(self._read_registers(desc.register_address, desc.register_count, desc.data_type, desc.scale, read_func_to_use))
                     valid_sensor_descriptions.append(desc)

                valid_rw_params = []
                 # Smyčka pro RW registry
                for key, params in RW_REGISTER_MAP.items():
                    rw_count = params.get('count', 1)
                    rw_type = params.get('data_type', 'U16')
                    rw_scale = params.get('scale', 1.0)
                    # Použijeme vždy stejnou funkci (v této verzi)
                    tasks.append(self._read_registers(params['address'], rw_count, rw_type, rw_scale, read_func_to_use))
                    valid_rw_params.append((key, params))

                # Spustíme všechny čtecí úlohy paralelně
                results = await asyncio.gather(*tasks)

                # Zpracujeme výsledky
                result_index = 0
                for desc in valid_sensor_descriptions:
                    value = results[result_index]
                    if value is not None: data[desc.key] = value
                    result_index += 1
                for key, params in valid_rw_params:
                    value = results[result_index]
                    if value is not None: data[key] = value
                    result_index += 1

                end_time = asyncio.get_event_loop().time()
                _LOGGER.debug(f"ASYNC Čtení dat dokončeno za {end_time - start_time:.3f} sekund. Získáno klíčů: {len(data)}")

                if not data and (valid_sensor_descriptions or valid_rw_params):
                     _LOGGER.warning("Nezískaná žádná data z ASYNC čtení, i když definice existují.")

                return data

            except ConnectionException as err:
                _LOGGER.warning(f"ASYNC Chyba připojení při aktualizaci dat: {err}")
                if self._client.connected: self._client.close()
                raise UpdateFailed(f"ASYNC Chyba připojení: {err}") from err
            except Exception as err:
                _LOGGER.error(f"Neočekávaná chyba v ASYNC _async_update_data: {err}", exc_info=True)
                if self._client.connected: self._client.close()
                raise UpdateFailed(f"Neočekávaná chyba v ASYNC update: {err}") from err

    # --- ASYNCHRONNÍ Metody pro zápis ---
    # Používají také explicitní pojmenování argumentů a slave=

    async def async_write_register(self, address: int, value: int):
        """Zapíše jeden 16bitový registr (Holding) ASYNCHRONNĚ."""
        async with self._lock:
            try:
                is_connected = await self._ensure_connection()
                if not is_connected:
                    _LOGGER.error(f"ASYNC Zápis selhal: Nepodařilo se připojit k {self.host}:{self.port}")
                    return False
                _LOGGER.debug(f"Pokus o ASYNC zápis hodnoty {value} na adresu {address} (Slave: {self.slave_id})")
                result = await self._client.write_register(address=address, value=value, slave=self.slave_id)
                if result.isError():
                    _LOGGER.error(f"ASYNC Modbus chyba při zápisu na adresu {address}: {result}")
                    return False
                else:
                    _LOGGER.info(f"ASYNC Úspěšně zapsána hodnota {value} na adresu {address}")
                    await self.async_request_refresh()
                    return True
            except Exception as e:
                _LOGGER.error(f"Neočekávaná chyba při ASYNC zápisu na adresu {address}: {e}", exc_info=True)
                return False

    async def async_write_multiple_registers(self, address: int, values: list[int]):
        """Zapíše více 16bitových registrů (Holding) ASYNCHRONNĚ."""
        async with self._lock:
            try:
                is_connected = await self._ensure_connection()
                if not is_connected:
                    _LOGGER.error(f"ASYNC Zápis více registrů selhal: Nepodařilo se připojit k {self.host}:{self.port}")
                    return False
                _LOGGER.debug(f"Pokus o ASYNC zápis hodnot {values} od adresy {address} (Slave: {self.slave_id})")
                result = await self._client.write_registers(address=address, values=values, slave=self.slave_id)
                if result.isError():
                    _LOGGER.error(f"ASYNC Modbus chyba při zápisu více registrů od adresy {address}: {result}")
                    return False
                else:
                    _LOGGER.info(f"ASYNC Úspěšně zapsány hodnoty {values} od adresy {address}")
                    await self.async_request_refresh()
                    return True
            except Exception as e:
                _LOGGER.error(f"Neočekávaná chyba při ASYNC zápisu více registrů od adresy {address}: {e}", exc_info=True)
                return False