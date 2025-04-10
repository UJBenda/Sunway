# custom_components/sunway_fve/__init__.py
import logging
import asyncio
from datetime import timedelta
from pymodbus.client import ModbusTcpClient # Nebo ModbusSerialClient atd.
from pymodbus.exceptions import ConnectionException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_SLAVE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.modbus import async_get_modbus_hub # Pro využití sdíleného hubu

from .const import DOMAIN, SENSOR_DESCRIPTIONS, RW_REGISTER_MAP # Importujte své konstanty

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "switch", "number"] # Přidejte/odeberte platformy podle potřeby

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sunway FVE from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave_id = entry.data[CONF_SLAVE]
    scan_interval = timedelta(seconds=entry.data[CONF_SCAN_INTERVAL])

    _LOGGER.debug(f"Setting up Sunway FVE integration for {host}:{port} (Slave ID: {slave_id})")

    # Vytvoření Modbus klienta - Zvažte použití sdíleného Modbus hubu pro lepší správu
    # client = ModbusTcpClient(host, port=port)
    # hass.data[DOMAIN][entry.entry_id] = {"client": client}

    # Vytvoření coordinatora pro pravidelné načítání dat
    coordinator = SunwayFveCoordinator(hass, host, port, slave_id, scan_interval)

    # První načtení dat pro ověření spojení a získání počátečních hodnot
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Předání nastavení platformám (sensor, switch, ...)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # TODO: Přidat listener pro aktualizaci options, pokud je implementujete

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Ukončení spojení a odstranění dat
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # if isinstance(coordinator, SunwayFveCoordinator): # Ověření typu
        #     await coordinator.async_shutdown() # Pokud máte metodu na zavření klienta v coordinatoru
        # Zavření klienta, pokud není spravován coordinatorem
        # client = hass.data[DOMAIN][entry.entry_id].get("client")
        # if client:
        #     client.close()

    return unload_ok

class SunwayFveCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Sunway FVE."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, slave_id: int, scan_interval: timedelta):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
        )
        self.host = host
        self.port = port
        self.slave_id = slave_id
        # Vytvořte klienta zde, bude spravován coordinatorem
        self._client = ModbusTcpClient(host, port=port)
        # Můžete použít i: self._hub = async_get_modbus_hub(hass, ...) pro sdílený hub

    def _read_registers(self, address: int, count: int, data_type: str, scale: float) -> any:
        """Helper to read and decode registers."""
        # POZOR: Zvolte správnou funkci čtení - read_holding_registers (0x03) nebo read_input_registers (0x04)
        # Většina stavových registrů bývá Input (RO), konfigurační Holding (RW). Ověřte!
        # Zde předpokládám Holding pro všechny pro zjednodušení.
        try:
            # Zkuste optimalizovat čtení do bloků, pokud jsou registry blízko sebe
            result = self._client.read_holding_registers(address, count, slave=self.slave_id)
            if result.isError():
                _LOGGER.debug(f"Modbus error reading {count} registers from {address}: {result}")
                return None # Nebo vyvolejte výjimku

            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
            # Zpracování podle data_type
            raw_value = None
            if data_type == "U16":
                raw_value = decoder.decode_16bit_uint()
            elif data_type == "I16":
                raw_value = decoder.decode_16bit_int()
            elif data_type == "U32":
                raw_value = decoder.decode_32bit_uint()
            elif data_type == "I32":
                 raw_value = decoder.decode_32bit_int()
            elif data_type == "STR":
                 # Pro stringy je potřeba číst více registrů a dekódovat je
                 raw_value = decoder.decode_string(count * 2).rstrip(b'\x00').decode('utf-8') # *2 protože registr má 2 bajty
            # Přidejte další typy (např. 64bit) pokud je potřeba

            if raw_value is not None:
                 if data_type != "STR": # Scale neaplikujeme na string
                     if scale != 1.0:
                         if scale > 1:
                             return raw_value / scale
                         else: # scale < 1 (např. 0.1)
                             return raw_value * scale
                     else:
                         return raw_value
                 else:
                    return raw_value # Vracíme string
            return None

        except ConnectionException as e:
            _LOGGER.debug(f"Modbus connection error: {e}")
            raise UpdateFailed(f"Modbus connection error: {e}") from e
        except Exception as e:
            _LOGGER.error(f"Error reading Modbus register {address}: {e}")
            return None # Vrací None při jiné chybě čtení

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        data = {}
        try:
            # Připojení k Modbus zařízení (pokud není trvale otevřené)
            if not self._client.is_socket_open():
               self._client.connect() # Zpracujte výjimky

            # Čtení všech potřebných registrů - optimalizujte do bloků!
            for desc in SENSOR_DESCRIPTIONS:
                # Optimalizace: Místo čtení každého registru zvlášť, seskupte je
                # a přečtěte v blocích. Toto je jen základní příklad.
                value = await self.hass.async_add_executor_job(
                    self._read_registers, desc.register_address, desc.register_count, desc.data_type, desc.scale
                )
                data[desc.key] = value
                _LOGGER.debug(f"Read {desc.key}: Address={desc.register_address}, Value={value}")

            # Načtení RW registrů pro switche/numbers (pokud je chcete zobrazovat aktuální stav)
            for key, params in RW_REGISTER_MAP.items():
                desc = next((d for d in SENSOR_DESCRIPTIONS if d.key == key), None) # Najdi popis v sensors
                if desc: # Pokud existuje popis v sensors, použij ho
                    value = await self.hass.async_add_executor_job(
                        self._read_registers, desc.register_address, desc.register_count, desc.data_type, desc.scale
                     )
                elif 'data_type' in params and 'count' in params and 'scale' in params: # Pokud ne, použij data z RW_REGISTER_MAP
                     value = await self.hass.async_add_executor_job(
                        self._read_registers, params['address'], params['count'], params['data_type'], params['scale']
                     )
                else: # Pokud nemáme dost info, přeskočíme čtení
                    value = None
                    _LOGGER.warning(f"Skipping read for RW register {key} due to missing definition info")

                if value is not None:
                    data[key] = value
                    _LOGGER.debug(f"Read RW {key}: Address={params['address']}, Value={value}")


            # Uzavření spojení (pokud není trvale otevřené)
            # self._client.close() # Pokud chcete spojení zavírat po každém čtení

            if not data: # Pokud se nepodařilo nic přečíst
                raise UpdateFailed("No data received from inverter")

            return data
        except ConnectionException as err:
            # Pokud se nepodaří připojit, zavřeme spojení a vyvoláme chybu
            if self._client.is_socket_open():
                self._client.close()
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            # Pokud nastane jiná chyba při čtení
            if self._client.is_socket_open():
                self._client.close() # Pro jistotu zavřít
            raise UpdateFailed(f"Unknown error during update: {err}") from err

    async def async_shutdown(self) -> None:
        """Close the Modbus client connection."""
        if self._client.is_socket_open():
            self._client.close()
        await super().async_shutdown()

    # Přidejte metody pro zápis registrů (pro switche, numbers)
    async def async_write_register(self, address: int, value: int):
        """Write a single holding register."""
        # POZOR: Zápis je obvykle do Holding registrů (0x06 write single, 0x10 write multiple)
        _LOGGER.debug(f"Writing value {value} to register {address}")
        try:
            if not self._client.is_socket_open():
                self._client.connect() # Zpracujte výjimky
            # Použijte write_register pro jeden registr nebo write_registers pro více
            result = await self.hass.async_add_executor_job(
                 self._client.write_register, address, value, slave=self.slave_id
            )
            if result.isError():
                _LOGGER.error(f"Modbus error writing register {address}: {result}")
                return False
            # Po úspěšném zápisu je dobré spustit refresh dat coordinatora
            await self.async_request_refresh()
            return True
        except ConnectionException as e:
            _LOGGER.error(f"Modbus connection error during write: {e}")
            return False
        except Exception as e:
            _LOGGER.error(f"Error writing Modbus register {address}: {e}")
            return False

    async def async_write_multiple_registers(self, address: int, values: list[int]):
        """Write multiple holding registers."""
        # Potřebné pro zápis 32bit hodnot (které zabírají 2 registry)
        _LOGGER.debug(f"Writing multiple values {values} to starting register {address}")
        try:
            if not self._client.is_socket_open():
                self._client.connect()
            result = await self.hass.async_add_executor_job(
                self._client.write_registers, address, values, slave=self.slave_id
            )
            if result.isError():
                _LOGGER.error(f"Modbus error writing multiple registers at {address}: {result}")
                return False
            await self.async_request_refresh()
            return True
        except ConnectionException as e:
            _LOGGER.error(f"Modbus connection error during multiple write: {e}")
            return False
        except Exception as e:
            _LOGGER.error(f"Error writing multiple Modbus registers at {address}: {e}")
            return False