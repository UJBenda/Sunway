# custom_components/sunway_fve/const.py
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    PERCENTAGE,
    TIME_HOURS,
)
from dataclasses import dataclass
from typing import Optional

DOMAIN = "sunway_fve"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 30 # Sekundy

# Pomocná datová třída pro definici registru/senzoru
@dataclass
class SunwayModbusSensorEntityDescription:
    key: str # Unikátní klíč pro HA entitu
    name: str # Název entity v HA
    register_address: int # Modbus adresa
    register_count: int # Počet registrů ke čtení (1 pro U16/I16, 2 pro U32/I32, atd.)
    data_type: str # Typ dat (U16, I16, U32, I32, STR)
    unit: Optional[str] = None # Jednotka měření
    device_class: Optional[SensorDeviceClass] = None
    state_class: Optional[SensorStateClass] = None
    scale: float = 1.0 # Dělitel/násobitel (Accuracy)
    read_only: bool = True # Je registr RO?
    # Můžete přidat další pole podle potřeby (např. pro parsování bitů, enum mapování)

# Zde převedete řádky z Register Bytes Function.txt do struktury
# POZOR: Důkladně zkontrolujte 'Accuracy', 'Type', 'Bytes' a počet registrů!
# Accuracy > 1 znamená dělit tímto číslem. Accuracy < 1 znamená násobit tímto číslem.
# Pro U32/I32 typicky potřebujete číst 2 registry. Pro STR podle počtu Bytes.
# Pro RTC (registry 20000-20002) je potřeba speciální logika parsování.
# Pro registry s odkazy na tabulky (3.2, 3.3, 3.6) je potřeba tyto tabulky získat a implementovat logiku.

SENSOR_DESCRIPTIONS: list[SunwayModbusSensorEntityDescription] = [
    # --- Příklady RO (Read Only) senzorů ---
    SunwayModbusSensorEntityDescription(
        key="inverter_sn", name="Inverter Serial Number", register_address=10000, register_count=8, data_type="STR", read_only=True
    ),
    SunwayModbusSensorEntityDescription(
        key="running_status", name="Inverter Running Status", register_address=10105, register_count=1, data_type="U16", read_only=True,
        # Zde by bylo potřeba mapování čísel na stavy podle poznámky v souboru
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_a_voltage", name="Grid Phase A Voltage", register_address=11001, register_count=1, data_type="U16", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=10.0, read_only=True
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_a_current", name="Grid Phase A Current", register_address=11002, register_count=1, data_type="U16", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=10.0, read_only=True
    ),
     SunwayModbusSensorEntityDescription(
        key="grid_frequency", name="Grid Frequency", register_address=11007, register_count=1, data_type="U16", unit=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, scale=100.0, read_only=True
    ),
    SunwayModbusSensorEntityDescription(
        key="power_ac", name="AC Power", register_address=11008, register_count=2, data_type="I32", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1000.0, read_only=True
    ),
    SunwayModbusSensorEntityDescription(
        key="pv_gen_today", name="PV Generation Today", register_address=11010, register_count=2, data_type="U32", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=10.0, read_only=True
    ),
     SunwayModbusSensorEntityDescription(
        key="pv_gen_total", name="PV Generation Total", register_address=11012, register_count=2, data_type="U32", unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=10.0, read_only=True
    ),
     SunwayModbusSensorEntityDescription(
        key="pv_total_power", name="PV Input Total Power", register_address=11016, register_count=2, data_type="U32", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1000.0, read_only=True
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_1", name="Temperature Sensor 1", register_address=11018, register_count=1, data_type="I16", unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, scale=10.0, read_only=True
    ),
    SunwayModbusSensorEntityDescription(
        key="pv1_voltage", name="PV1 Voltage", register_address=11028, register_count=1, data_type="U16", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=10.0, read_only=True
    ),
     SunwayModbusSensorEntityDescription(
        key="pv1_current", name="PV1 Current", register_address=11029, register_count=1, data_type="U16", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=10.0, read_only=True
    ),
    # ... přidejte další RO registry zde ...
    SunwayModbusSensorEntityDescription(
        key="battery_voltage", name="Battery Voltage", register_address=40254, register_count=1, data_type="U16", unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=10.0, read_only=True
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_current", name="Battery Current", register_address=40255, register_count=1, data_type="I16", unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=10.0, read_only=True # Pozor I16 = může být záporný (vybíjení)
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_power", name="Battery Power", register_address=40258, register_count=2, data_type="I32", unit=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1000.0, read_only=True # Pozor I32 = může být záporný (vybíjení)
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_soc", name="Battery SOC", register_address=43000, register_count=1, data_type="U16", unit=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT, scale=100.0, read_only=True
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_soh", name="Battery SOH", register_address=43001, register_count=1, data_type="U16", unit=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT, scale=100.0, read_only=True # SOH není standardní device class, zobrazí se jako %
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_pack_temp", name="BMS Pack Temperature", register_address=43003, register_count=1, data_type="U16", unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, scale=10.0, read_only=True
    ),
    # --- Příklady RW (Read/Write) registrů, které mohou být i senzory ---
    SunwayModbusSensorEntityDescription(
        key="grid_injection_limit_status", name="Grid Injection Power Limit Status", register_address=25100, register_count=1, data_type="U16", read_only=False # Zde bude potřeba mapování 0=Off, 1=On
    ),
     SunwayModbusSensorEntityDescription(
        key="grid_injection_limit_setting", name="Grid Injection Power Limit Setting", register_address=25103, register_count=1, data_type="U16", unit=PERCENTAGE, scale=0.1, read_only=False # scale 0.1 = násobit 0.1 (dělit 10)
    ),
     SunwayModbusSensorEntityDescription(
        key="eps_ups_switch_status", name="EPS/UPS Function Switch Status", register_address=50001, register_count=1, data_type="U16", read_only=False # Zde bude potřeba mapování 0=Off, 1=On
    ),
    # ... přidejte další RW registry zde, pokud je chcete číst jako senzory ...
]

# Zde můžete definovat podobné struktury pro Switche, Numbers, Selects pro RW registry
# Např. pro Switch:
@dataclass
class SunwayModbusSwitchEntityDescription:
     key: str
     name: str
     register_address: int
     # ... další potřebné info pro zápis

@dataclass
class SunwayModbusNumberEntityDescription:
     key: str
     name: str
     register_address: int
     register_count: int # Obvykle 1 pro U16/I16, 2 pro U32/I32
     data_type: str
     scale: float
     unit: Optional[str] = None
     min_value: Optional[float] = None
     max_value: Optional[float] = None
     step: Optional[float] = None
     mode: str = "auto" # "box" nebo "slider"
     # ...

# Příklad definice pro RW registry (pro sensor.py, switch.py, number.py):
RW_REGISTER_MAP = {
    "grid_injection_limit_switch": {"address": 25100, "type": "switch", "write_map": {True: 1, False: 0}},
    "grid_injection_limit_setting": {"address": 25103, "type": "number", "scale": 0.1, "unit": "%", "min": 0.0, "max": 100.0, "step": 0.1, "data_type": "U16", "count": 1},
    "eps_ups_switch": {"address": 50001, "type": "switch", "write_map": {True: 1, False: 0}},
    "off_grid_voltage": {"address": 50004, "type": "number", "scale": 10.0, "unit": "V", "data_type": "U16", "count": 1}, # Zjistit min/max/step
    "off_grid_frequency": {"address": 50005, "type": "number", "scale": 100.0, "unit": "Hz", "min": 45.0, "max": 65.0, "step": 0.01, "data_type": "U16", "count": 1},
    # ... atd. pro další RW registry 50006, 50007, 50009, 50202-50207 ...
}