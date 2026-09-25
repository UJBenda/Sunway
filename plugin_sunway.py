# Verze pluginu: 2026.05.13.Fix_V3_Architecture_Negative_Values
# Kompatibilita: Home Assistant 2025.11+ / Solax Modbus 2025.x a novější (V3 Architecture)
#
# HISTORIE A POPIS ZMĚN:
# 2026.05.13 - Navrácení ochrany proti záporným hodnotám (noční resety). 
#              Denní výroba a energie (41005, 41001, 41000 atd.) čteny jako REGISTER_S16.
#              Aplikována funkce 'value_function_energy_no_negative' pro odfiltrování záporných čísel.
# 2026.05.08 - Kompletní přepis na novou architekturu (odstraněn parametr 'unit', nahrazen za 'register_data_type').
#              Oprava inicializace pluginu (přidáno 'kw_only=True' a 'TIME_TYPES=[]').

import logging
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

# Importy pro novou architekturu [cite: 8]
from .pymodbus_compat import DataType, convert_from_registers
from custom_components.solax_modbus.const import *

_LOGGER = logging.getLogger(__name__)

# ============================================================================================
# Identifikátor střídače
SUNWAY_STT_10KTL = 0x0001
ALLDEFAULT = SUNWAY_STT_10KTL
# ============================================================================================

# ====================================== KONSTANTY ===============================================
PERIOD_OFFSET = 7
PERIOD_BASE_REG = 53007
TIME_HOUR_SCALE = 256
# ============================================================================================

# Nová architektura vyžaduje register_data_type místo unit a frozen dataclass [cite: 4]
@dataclass(kw_only=True, frozen=True)
class SunwayModbusButtonEntityDescription(BaseModbusButtonEntityDescription):
    allowedtypes: int = ALLDEFAULT
    register_data_type: str = REGISTER_U16

@dataclass(kw_only=True, frozen=True)
class SunwayModbusNumberEntityDescription(BaseModbusNumberEntityDescription):
    allowedtypes: int = ALLDEFAULT
    register_data_type: str = REGISTER_U16

@dataclass(kw_only=True, frozen=True)
class SunwayModbusSelectEntityDescription(BaseModbusSelectEntityDescription):
    allowedtypes: int = ALLDEFAULT
    register_data_type: str = REGISTER_U16

@dataclass(kw_only=True, frozen=True)
class SunwayModbusSwitchEntityDescription(BaseModbusSwitchEntityDescription):
    allowedtypes: int = ALLDEFAULT
    register_data_type: str = REGISTER_U16

@dataclass(kw_only=True, frozen=True)
class SunwayModbusSensorEntityDescription(BaseModbusSensorEntityDescription):
    allowedtypes: int = ALLDEFAULT
    register_data_type: str = REGISTER_U16
    register_type: int = REG_HOLDING

# ====================================== POMOCNÉ FUNKCE ===============================================

TIME_OPTIONS_SUNWAY: Dict[int, str] = {}
for h in range(24):
    for m in range(0, 60, 5):
        TIME_OPTIONS_SUNWAY[h * TIME_HOUR_SCALE + m] = f"{h:02d}:{m:02d}"

def sunway_rtc_function(initval: List[int], descr: Any, datadict: Dict[str, Any]) -> Optional[datetime]:
    """Dekóduje RTC čas ze tří registrů."""
    try:
        year_month = initval[0]
        day_hour = initval[1]
        min_sec = initval[2]
        
        year = (year_month >> 8) + 2000
        month = year_month & 0xFF
        day = day_hour >> 8
        hour = day_hour & 0xFF
        minute = min_sec >> 8
        second = min_sec & 0xFF
        return datetime(year, month, day, hour, minute, second)
    except (ValueError, TypeError, IndexError):
        return None

def value_function_sync_rtc_sunway(initval: Any, descr: Any, datadict: Dict[str, Any]) -> List[Tuple[str, int]]:
    """Vytvoří payload pro synchronizaci času."""
    now = dt_util.now()  # čas v časové zóně HA, ne systémový (v HA OS často UTC)
    year_val = now.year % 100
    return [
        (REGISTER_U16, (year_val << 8) | now.month),
        (REGISTER_U16, (now.day << 8) | now.hour),
        (REGISTER_U16, (now.minute << 8) | now.second)
    ]

def create_period_write_payload(period_num: int, data: Dict[str, Any]) -> Optional[List[Tuple[str, int]]]:
    """Sestaví payload pro zápis jedné periody nabíjení/vybíjení."""
    start_time_str = data.get(f"period_{period_num}_start_time", "00:00")
    stop_time_str = data.get(f"period_{period_num}_stop_time", "00:00")
    power_limit_pct = data.get(f"period_{period_num}_power_limit", 0.0)
    try:
        mode_str = data.get(f"period_{period_num}_charge_discharge_mode", "Žádný")
        ac_charge = data.get(f"period_{period_num}_ac_charge_enable", False)
        
        charge_discharge_setting = 2 if mode_str == "Vybíjení" else 1 if mode_str == "Nabíjení" else 0
        battery_charge_by = 1 if ac_charge else 0
        power_limit_val = int(float(power_limit_pct) * 10)
        
        start_h, start_m = map(int, start_time_str.split(":"))
        stop_h, stop_m = map(int, stop_time_str.split(":"))
        start_time_val = (start_h * TIME_HOUR_SCALE + start_m)
        stop_time_val = (stop_h * TIME_HOUR_SCALE + stop_m)
        
        return [
            (REGISTER_U16, charge_discharge_setting),
            (REGISTER_U16, battery_charge_by),
            (REGISTER_U16, 0xFFFF),
            (REGISTER_U16, power_limit_val),
            (REGISTER_U16, 0xFFFF),
            (REGISTER_U16, start_time_val),
            (REGISTER_U16, stop_time_val)
        ]
    except (ValueError, TypeError) as e:
        _LOGGER.error(f"Sunway: Chyba formátu dat pro periodu {period_num}: {e}")
        return None

def decode_sunway_time(val: Optional[int], _, __) -> str:
    if val is None: return "N/A"
    return f"{(val >> 8):02d}:{(val & 0xFF):02d}"

def create_periods_enable_payload(i: Any, d: Any, data: Dict[str, Any]) -> List[Tuple[str, int]]:
    periods_enable_mask = 0
    for period_num in range(1, 7):
        if data.get(f"period_{period_num}_charge_discharge_enable", False):
            periods_enable_mask |= 1 << (period_num - 1)
    return [(REGISTER_U16, periods_enable_mask)]

def value_function_energy_no_negative(val: Any, descr: Any, datadict: Dict[str, Any]) -> Optional[float]:
    """
    KLÍČOVÁ FUNKCE: Ochrana proti záporným hodnotám v noci (reset střídače).
    Neplatná (záporná) hodnota vrací None -> senzor je chvíli "unknown".
    Vracet 0.0 nelze: u TOTAL_INCREASING by HA pokles na 0 bral jako reset
    a po návratu skutečné hodnoty by se denní energie započítala podruhé.
    """
    if val is None or val < 0:
        return None
    return round(val * 0.1, 1)

# ================================= DEFINICE ENTIT =============================================

BUTTON_TYPES = [
    SunwayModbusButtonEntityDescription(name="Synchronizovat čas", key="sync_rtc", register=20000, write_method=WRITE_MULTI_MODBUS, value_function=value_function_sync_rtc_sunway, entity_category=EntityCategory.CONFIG, icon="mdi:clock-sync-outline"),
    SunwayModbusButtonEntityDescription(name="Uložit nastavení Periody 1", key="save_period_1", register=PERIOD_BASE_REG + 0 * PERIOD_OFFSET, write_method=WRITE_MULTI_MODBUS, value_function=lambda i, d, data: create_period_write_payload(1, data), entity_category=EntityCategory.CONFIG, icon="mdi:content-save-settings"),
    SunwayModbusButtonEntityDescription(name="Uložit nastavení Periody 2", key="save_period_2", register=PERIOD_BASE_REG + 1 * PERIOD_OFFSET, write_method=WRITE_MULTI_MODBUS, value_function=lambda i, d, data: create_period_write_payload(2, data), entity_category=EntityCategory.CONFIG, icon="mdi:content-save-settings"),
    SunwayModbusButtonEntityDescription(name="Uložit nastavení Periody 3", key="save_period_3", register=PERIOD_BASE_REG + 2 * PERIOD_OFFSET, write_method=WRITE_MULTI_MODBUS, value_function=lambda i, d, data: create_period_write_payload(3, data), entity_category=EntityCategory.CONFIG, icon="mdi:content-save-settings"),
    SunwayModbusButtonEntityDescription(name="Uložit nastavení Periody 4", key="save_period_4", register=PERIOD_BASE_REG + 3 * PERIOD_OFFSET, write_method=WRITE_MULTI_MODBUS, value_function=lambda i, d, data: create_period_write_payload(4, data), entity_category=EntityCategory.CONFIG, icon="mdi:content-save-settings"),
    SunwayModbusButtonEntityDescription(name="Uložit nastavení Periody 5", key="save_period_5", register=PERIOD_BASE_REG + 4 * PERIOD_OFFSET, write_method=WRITE_MULTI_MODBUS, value_function=lambda i, d, data: create_period_write_payload(5, data), entity_category=EntityCategory.CONFIG, icon="mdi:content-save-settings"),
    SunwayModbusButtonEntityDescription(name="Uložit nastavení Periody 6", key="save_period_6", register=PERIOD_BASE_REG + 5 * PERIOD_OFFSET, write_method=WRITE_MULTI_MODBUS, value_function=lambda i, d, data: create_period_write_payload(6, data), entity_category=EntityCategory.CONFIG, icon="mdi:content-save-settings"),
    SunwayModbusButtonEntityDescription(name="Uložit aktivaci period", key="save_periods_enable_state", register=53006, write_method=WRITE_MULTI_MODBUS, value_function=create_periods_enable_payload, entity_category=EntityCategory.CONFIG, icon="mdi:calendar-check"),
    SunwayModbusButtonEntityDescription(name="EMS Keep-Alive", key="ems_keep_alive", register=25104, command=1, write_method=WRITE_SINGLE_MODBUS, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:heart-pulse"),
]

NUMBER_TYPES = [
    SunwayModbusNumberEntityDescription(name="Nastavení limitu dodávky do sítě", key="grid_injection_power_limit_setting", register=25103, fmt="f", native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=0.1, native_unit_of_measurement=PERCENTAGE, device_class=NumberDeviceClass.POWER_FACTOR, write_method=WRITE_SINGLE_MODBUS, entity_category=EntityCategory.CONFIG),
    SunwayModbusNumberEntityDescription(name="Nastavení napětí v Off-grid režimu", key="off_grid_voltage_setting", register=50004, fmt="f", native_min_value=200.0, native_max_value=250.0, native_step=0.1, scale=0.1, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=NumberDeviceClass.VOLTAGE, write_method=WRITE_SINGLE_MODBUS, entity_category=EntityCategory.CONFIG),
    SunwayModbusNumberEntityDescription(name="Nastavení frekvence v Off-grid režimu", key="off_grid_frequency_setting", register=50005, fmt="f", native_min_value=45.00, native_max_value=65.00, native_step=0.01, scale=0.01, native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=NumberDeviceClass.FREQUENCY, write_method=WRITE_SINGLE_MODBUS, entity_category=EntityCategory.CONFIG),
    SunwayModbusNumberEntityDescription(name="Nastavení maximálního výkonu ze sítě", key="max_grid_power_value_setting", register=50009, fmt="f", native_min_value=0, native_max_value=20, native_step=0.1, scale=0.1, native_unit_of_measurement="kVA", device_class=NumberDeviceClass.APPARENT_POWER, write_method=WRITE_SINGLE_MODBUS, entity_category=EntityCategory.CONFIG),
    SunwayModbusNumberEntityDescription(name="On-grid DOD baterie", key="on_grid_battery_dod", register=52503, fmt="f", native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=0.1, native_unit_of_measurement=PERCENTAGE, write_method=WRITE_SINGLE_MODBUS, entity_category=EntityCategory.CONFIG, icon="mdi:battery-arrow-down"),
    SunwayModbusNumberEntityDescription(name="Off-grid DOD baterie", key="off_grid_battery_dod", register=52505, fmt="f", native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=0.1, native_unit_of_measurement=PERCENTAGE, write_method=WRITE_SINGLE_MODBUS, entity_category=EntityCategory.CONFIG, icon="mdi:battery-arrow-down-outline"),
    SunwayModbusNumberEntityDescription(name="Perioda 1: Limit výkonu (%)", key="period_1_power_limit", write_method=WRITE_DATA_LOCAL, native_unit_of_measurement=PERCENTAGE, device_class=NumberDeviceClass.POWER_FACTOR, native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=1, entity_category=EntityCategory.CONFIG, initvalue=100.0),
    SunwayModbusNumberEntityDescription(name="Perioda 2: Limit výkonu (%)", key="period_2_power_limit", write_method=WRITE_DATA_LOCAL, native_unit_of_measurement=PERCENTAGE, device_class=NumberDeviceClass.POWER_FACTOR, native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=1, entity_category=EntityCategory.CONFIG, initvalue=100.0),
    SunwayModbusNumberEntityDescription(name="Perioda 3: Limit výkonu (%)", key="period_3_power_limit", write_method=WRITE_DATA_LOCAL, native_unit_of_measurement=PERCENTAGE, device_class=NumberDeviceClass.POWER_FACTOR, native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=1, entity_category=EntityCategory.CONFIG, initvalue=100.0),
    SunwayModbusNumberEntityDescription(name="Perioda 4: Limit výkonu (%)", key="period_4_power_limit", write_method=WRITE_DATA_LOCAL, native_unit_of_measurement=PERCENTAGE, device_class=NumberDeviceClass.POWER_FACTOR, native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=1, entity_category=EntityCategory.CONFIG, initvalue=100.0),
    SunwayModbusNumberEntityDescription(name="Perioda 5: Limit výkonu (%)", key="period_5_power_limit", write_method=WRITE_DATA_LOCAL, native_unit_of_measurement=PERCENTAGE, device_class=NumberDeviceClass.POWER_FACTOR, native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=1, entity_category=EntityCategory.CONFIG, initvalue=100.0),
    SunwayModbusNumberEntityDescription(name="Perioda 6: Limit výkonu (%)", key="period_6_power_limit", write_method=WRITE_DATA_LOCAL, native_unit_of_measurement=PERCENTAGE, device_class=NumberDeviceClass.POWER_FACTOR, native_min_value=0.0, native_max_value=100.0, native_step=0.1, scale=1, entity_category=EntityCategory.CONFIG, initvalue=100.0),
    SunwayModbusNumberEntityDescription(name="EMS: Výkon baterie", key="ems_battery_power_setting", register=50207, write_method=WRITE_SINGLE_MODBUS, fmt="i", native_min_value=-10000, native_max_value=10000, native_step=100, register_data_type=REGISTER_S16, scale=10, native_unit_of_measurement=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_category=EntityCategory.CONFIG, icon="mdi:battery-charging-high"),
    SunwayModbusNumberEntityDescription(name="EMS: Cílový AC výkon (celkový)", key="ems_total_ac_power_setting", register=50203, write_method=WRITE_SINGLE_MODBUS, fmt="i", native_min_value=-10000, native_max_value=10000, native_step=100, register_data_type=REGISTER_S16, scale=10, native_unit_of_measurement=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_category=EntityCategory.CONFIG, icon="mdi:transmission-tower"),
    SunwayModbusNumberEntityDescription(name="EMS: Cílový AC výkon Fáze A", key="ems_phase_a_power_setting", register=50204, write_method=WRITE_SINGLE_MODBUS, fmt="i", native_min_value=-5000, native_max_value=5000, native_step=100, register_data_type=REGISTER_S16, scale=10, native_unit_of_measurement=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_category=EntityCategory.CONFIG),
    SunwayModbusNumberEntityDescription(name="EMS: Cílový AC výkon Fáze B", key="ems_phase_b_power_setting", register=50205, write_method=WRITE_SINGLE_MODBUS, fmt="i", native_min_value=-5000, native_max_value=5000, native_step=100, register_data_type=REGISTER_S16, scale=10, native_unit_of_measurement=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_category=EntityCategory.CONFIG),
    SunwayModbusNumberEntityDescription(name="EMS: Cílový AC výkon Fáze C", key="ems_phase_c_power_setting", register=50206, write_method=WRITE_SINGLE_MODBUS, fmt="i", native_min_value=-5000, native_max_value=5000, native_step=100, register_data_type=REGISTER_S16, scale=10, native_unit_of_measurement=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_category=EntityCategory.CONFIG),
    SunwayModbusNumberEntityDescription(name="Nastavení FV výkonu", key="pv_power_setting", register=50211, write_method=WRITE_SINGLE_MODBUS, fmt="i", native_min_value=0, native_max_value=20000, native_step=100, scale=1, native_unit_of_measurement=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_category=EntityCategory.CONFIG),
]

SELECT_TYPES = [
    SunwayModbusSelectEntityDescription(name="Pracovní režim hybridního střídače", key="hybrid_inverter_working_mode", register=50000, option_dict={1: "Obecný režim", 2: "Ekonomický režim", 3: "Režim UPS", 258: "EMS Obecný režim", 259: "EMS Režim řízení AC", 513: "EMS Režim řízení baterie", 772: "EMS Off-Grid režim"}, entity_category=EntityCategory.CONFIG),
    SunwayModbusSelectEntityDescription(name="Režim nastavení AC výkonu střídače", key="inverter_ac_power_setting_mode", register=50202, option_dict={0: "Vypnuto", 1: "Nastavení celkového výkonu", 2: "Nastavení výkonu pro každou fázi"}, entity_category=EntityCategory.CONFIG),
    SunwayModbusSelectEntityDescription(name="Nastavení priority výstupního výkonu", key="priority_power_output_setting", register=50210, option_dict={0: "Priorita výstupu z FV", 1: "Priorita výstupu z baterie"}, entity_category=EntityCategory.CONFIG),
    SunwayModbusSelectEntityDescription(name="Perioda 1: Režim Nabíjení/Vybíjení", key="period_1_charge_discharge_mode", write_method=WRITE_DATA_LOCAL, option_dict={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, entity_category=EntityCategory.CONFIG, initvalue="Žádný"),
    SunwayModbusSelectEntityDescription(name="Perioda 1: Čas začátku", key="period_1_start_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-start", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 1: Čas konce", key="period_1_stop_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-end", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 2: Režim Nabíjení/Vybíjení", key="period_2_charge_discharge_mode", write_method=WRITE_DATA_LOCAL, option_dict={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, entity_category=EntityCategory.CONFIG, initvalue="Žádný"),
    SunwayModbusSelectEntityDescription(name="Perioda 2: Čas začátku", key="period_2_start_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-start", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 2: Čas konce", key="period_2_stop_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-end", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 3: Režim Nabíjení/Vybíjení", key="period_3_charge_discharge_mode", write_method=WRITE_DATA_LOCAL, option_dict={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, entity_category=EntityCategory.CONFIG, initvalue="Žádný"),
    SunwayModbusSelectEntityDescription(name="Perioda 3: Čas začátku", key="period_3_start_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-start", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 3: Čas konce", key="period_3_stop_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-end", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 4: Režim Nabíjení/Vybíjení", key="period_4_charge_discharge_mode", write_method=WRITE_DATA_LOCAL, option_dict={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, entity_category=EntityCategory.CONFIG, initvalue="Žádný"),
    SunwayModbusSelectEntityDescription(name="Perioda 4: Čas začátku", key="period_4_start_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-start", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 4: Čas konce", key="period_4_stop_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-end", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 5: Režim Nabíjení/Vybíjení", key="period_5_charge_discharge_mode", write_method=WRITE_DATA_LOCAL, option_dict={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, entity_category=EntityCategory.CONFIG, initvalue="Žádný"),
    SunwayModbusSelectEntityDescription(name="Perioda 5: Čas začátku", key="period_5_start_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-start", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 5: Čas konce", key="period_5_stop_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-end", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 6: Režim Nabíjení/Vybíjení", key="period_6_charge_discharge_mode", write_method=WRITE_DATA_LOCAL, option_dict={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, entity_category=EntityCategory.CONFIG, initvalue="Žádný"),
    SunwayModbusSelectEntityDescription(name="Perioda 6: Čas začátku", key="period_6_start_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-start", initvalue="00:00"),
    SunwayModbusSelectEntityDescription(name="Perioda 6: Čas konce", key="period_6_stop_time", write_method=WRITE_DATA_LOCAL, option_dict=TIME_OPTIONS_SUNWAY, entity_category=EntityCategory.CONFIG, icon="mdi:clock-end", initvalue="00:00"),
]

SWITCH_TYPES = [
    SunwayModbusSwitchEntityDescription(name="Limit dodávky do sítě", key="grid_injection_power_limit_switch", register=25100, write_method=WRITE_SINGLE_MODBUS, register_bit=0, value_function=lambda bit, state, sk, d: 1 if state else 0, sensor_key="grid_injection_power_limit_switch_state"),
    SunwayModbusSwitchEntityDescription(name="Funkce EPS/UPS", key="eps_ups_function_switch", register=50001, write_method=WRITE_SINGLE_MODBUS, register_bit=0, value_function=lambda bit, state, sk, d: 1 if state else 0, sensor_key="eps_ups_function_switch_state"),
    SunwayModbusSwitchEntityDescription(name="Off-grid asymetrický výstup", key="off_grid_asymmetric_output_switch", register=50006, write_method=WRITE_SINGLE_MODBUS, register_bit=0, value_function=lambda bit, state, sk, d: 1 if state else 0, sensor_key="off_grid_asymmetric_output_switch_state"),
    SunwayModbusSwitchEntityDescription(name="Posun špičkové zátěže (Peak Shifting)", key="peak_load_shifting_switch", register=50007, write_method=WRITE_SINGLE_MODBUS, register_bit=0, value_function=lambda bit, state, sk, d: 1 if state else 0, sensor_key="peak_load_shifting_switch_state"),
    SunwayModbusSwitchEntityDescription(name="On-grid ochrana SOC baterie", key="on_grid_battery_soc_protection_switch", register=52502, write_method=WRITE_SINGLE_MODBUS, register_bit=0, value_function=lambda bit, state, sk, d: 1 if state else 0, sensor_key="on_grid_battery_soc_protection_switch_state", entity_category=EntityCategory.CONFIG, icon="mdi:battery-lock"),
    SunwayModbusSwitchEntityDescription(name="Off-grid ochrana SOC baterie", key="off_grid_battery_soc_protection_switch", register=52504, write_method=WRITE_SINGLE_MODBUS, register_bit=0, value_function=lambda bit, state, sk, d: 1 if state else 0, sensor_key="off_grid_battery_soc_protection_switch_state", entity_category=EntityCategory.CONFIG, icon="mdi:battery-lock-outline"),
    SunwayModbusSwitchEntityDescription(name="Zapnout/Vypnout Off-grid funkci", key="off_grid_function_switch", value_function=lambda bit, state, sk, d: 1 if state else 0, register=50200, write_method=WRITE_SINGLE_MODBUS),
    SunwayModbusSwitchEntityDescription(name="Vymazat příznak přetížení v Off-grid", key="clear_off_grid_overload_flag", value_function=lambda bit, state, sk, d: 1 if state else 0, register=50201, write_method=WRITE_SINGLE_MODBUS),
    SunwayModbusSwitchEntityDescription(name="Perioda 1: Povolit nabíjení/vybíjení", key="period_1_charge_discharge_enable", sensor_key="period_1_charge_discharge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 2: Povolit nabíjení/vybíjení", key="period_2_charge_discharge_enable", sensor_key="period_2_charge_discharge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 3: Povolit nabíjení/vybíjení", key="period_3_charge_discharge_enable", sensor_key="period_3_charge_discharge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 4: Povolit nabíjení/vybíjení", key="period_4_charge_discharge_enable", sensor_key="period_4_charge_discharge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 5: Povolit nabíjení/vybíjení", key="period_5_charge_discharge_enable", sensor_key="period_5_charge_discharge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 6: Povolit nabíjení/vybíjení", key="period_6_charge_discharge_enable", sensor_key="period_6_charge_discharge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 1: Povolit nabíjení ze sítě", key="period_1_ac_charge_enable", sensor_key="period_1_ac_charge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, icon="mdi:power-plug", initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 2: Povolit nabíjení ze sítě", key="period_2_ac_charge_enable", sensor_key="period_2_ac_charge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, icon="mdi:power-plug", initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 3: Povolit nabíjení ze sítě", key="period_3_ac_charge_enable", sensor_key="period_3_ac_charge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, icon="mdi:power-plug", initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 4: Povolit nabíjení ze sítě", key="period_4_ac_charge_enable", sensor_key="period_4_ac_charge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, icon="mdi:power-plug", initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 5: Povolit nabíjení ze sítě", key="period_5_ac_charge_enable", sensor_key="period_5_ac_charge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, icon="mdi:power-plug", initvalue=False),
    SunwayModbusSwitchEntityDescription(name="Perioda 6: Povolit nabíjení ze sítě", key="period_6_ac_charge_enable", sensor_key="period_6_ac_charge_enable", write_method=WRITE_DATA_LOCAL, entity_category=EntityCategory.CONFIG, icon="mdi:power-plug", initvalue=False),
]

SENSOR_TYPES = [
    SunwayModbusSensorEntityDescription(key="grid_injection_power_limit_switch_state", register=25100, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="eps_ups_function_switch_state", register=50001, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="off_grid_asymmetric_output_switch_state", register=50006, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="peak_load_shifting_switch_state", register=50007, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="on_grid_battery_soc_protection_switch_state", register=52502, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="off_grid_battery_soc_protection_switch_state", register=52504, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="grid_injection_power_limit_setting", register=25103, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="off_grid_voltage_setting", register=50004, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="off_grid_frequency_setting", register=50005, scale=0.01, internal=True),
    SunwayModbusSensorEntityDescription(key="max_grid_power_value_setting", register=50009, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="on_grid_battery_dod", register=52503, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="off_grid_battery_dod", register=52505, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="ems_battery_power_setting", register=50207, register_data_type=REGISTER_S16, scale=10, internal=True),
    SunwayModbusSensorEntityDescription(key="ems_total_ac_power_setting", register=50203, register_data_type=REGISTER_S16, scale=10, internal=True),
    SunwayModbusSensorEntityDescription(key="ems_phase_a_power_setting", register=50204, register_data_type=REGISTER_S16, scale=10, internal=True),
    SunwayModbusSensorEntityDescription(key="ems_phase_b_power_setting", register=50205, register_data_type=REGISTER_S16, scale=10, internal=True),
    SunwayModbusSensorEntityDescription(key="ems_phase_c_power_setting", register=50206, register_data_type=REGISTER_S16, scale=10, internal=True),
    SunwayModbusSensorEntityDescription(key="pv_power_setting", register=50211, scale=1, internal=True),
    SunwayModbusSensorEntityDescription(key="hybrid_inverter_working_mode", register=50000, scale={1: "Obecný režim", 2: "Ekonomický režim", 3: "Režim UPS", 258: "EMS Obecný režim", 259: "EMS Režim řízení AC", 513: "EMS Režim řízení baterie", 772: "EMS Off-Grid režim"}, internal=True),
    SunwayModbusSensorEntityDescription(key="inverter_ac_power_setting_mode", register=50202, scale={0: "Vypnuto", 1: "Nastavení celkového výkonu", 2: "Nastavení výkonu pro každou fázi"}, internal=True),
    SunwayModbusSensorEntityDescription(key="priority_power_output_setting", register=50210, scale={0: "Priorita výstupu z FV", 1: "Priorita výstupu z baterie"}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_1_charge_discharge_mode", register=PERIOD_BASE_REG + 0, scale={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_1_ac_charge_enable", register=PERIOD_BASE_REG + 1, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_1_power_limit", register=PERIOD_BASE_REG + 3, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="period_1_start_time", register=PERIOD_BASE_REG + 5, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_1_stop_time", register=PERIOD_BASE_REG + 6, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_2_charge_discharge_mode", register=PERIOD_BASE_REG + 1 * PERIOD_OFFSET + 0, scale={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_2_ac_charge_enable", register=PERIOD_BASE_REG + 1 * PERIOD_OFFSET + 1, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_2_power_limit", register=PERIOD_BASE_REG + 1 * PERIOD_OFFSET + 3, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="period_2_start_time", register=PERIOD_BASE_REG + 1 * PERIOD_OFFSET + 5, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_2_stop_time", register=PERIOD_BASE_REG + 1 * PERIOD_OFFSET + 6, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_3_charge_discharge_mode", register=PERIOD_BASE_REG + 2 * PERIOD_OFFSET + 0, scale={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_3_ac_charge_enable", register=PERIOD_BASE_REG + 2 * PERIOD_OFFSET + 1, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_3_power_limit", register=PERIOD_BASE_REG + 2 * PERIOD_OFFSET + 3, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="period_3_start_time", register=PERIOD_BASE_REG + 2 * PERIOD_OFFSET + 5, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_3_stop_time", register=PERIOD_BASE_REG + 2 * PERIOD_OFFSET + 6, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_4_charge_discharge_mode", register=PERIOD_BASE_REG + 3 * PERIOD_OFFSET + 0, scale={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_4_ac_charge_enable", register=PERIOD_BASE_REG + 3 * PERIOD_OFFSET + 1, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_4_power_limit", register=PERIOD_BASE_REG + 3 * PERIOD_OFFSET + 3, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="period_4_start_time", register=PERIOD_BASE_REG + 3 * PERIOD_OFFSET + 5, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_4_stop_time", register=PERIOD_BASE_REG + 3 * PERIOD_OFFSET + 6, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_5_charge_discharge_mode", register=PERIOD_BASE_REG + 4 * PERIOD_OFFSET + 0, scale={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_5_ac_charge_enable", register=PERIOD_BASE_REG + 4 * PERIOD_OFFSET + 1, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_5_power_limit", register=PERIOD_BASE_REG + 4 * PERIOD_OFFSET + 3, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="period_5_start_time", register=PERIOD_BASE_REG + 4 * PERIOD_OFFSET + 5, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_5_stop_time", register=PERIOD_BASE_REG + 4 * PERIOD_OFFSET + 6, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_6_charge_discharge_mode", register=PERIOD_BASE_REG + 5 * PERIOD_OFFSET + 0, scale={0: "Žádný", 1: "Nabíjení", 2: "Vybíjení"}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_6_ac_charge_enable", register=PERIOD_BASE_REG + 5 * PERIOD_OFFSET + 1, scale={0: False, 1: True}, internal=True),
    SunwayModbusSensorEntityDescription(key="period_6_power_limit", register=PERIOD_BASE_REG + 5 * PERIOD_OFFSET + 3, scale=0.1, internal=True),
    SunwayModbusSensorEntityDescription(key="period_6_start_time", register=PERIOD_BASE_REG + 5 * PERIOD_OFFSET + 5, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(key="period_6_stop_time", register=PERIOD_BASE_REG + 5 * PERIOD_OFFSET + 6, scale=decode_sunway_time, internal=True),
    SunwayModbusSensorEntityDescription(name="Sériové číslo střídače", key="inverter_sn", register=10000, register_data_type=REGISTER_STR, wordcount=4, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="Verze firmware", key="firmware_version", register=10011, register_data_type=REGISTER_U16, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="RTC", key="rtc", register=10100, register_data_type=REGISTER_WORDS, wordcount=3, scale=sunway_rtc_function, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:clock"),
    SunwayModbusSensorEntityDescription(name="Provozní stav střídače", key="inverter_running_status", register=10105, scale={0: "Čekání", 1: "Kontrola", 2: "V síti", 3: "Chyba", 4: "Aktualizace firmware", 5: "Mimo síť"}, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="Informace o zařízení", key="equipment_info", register=10008, scale=lambda val, desc, data: {(0x30, 0): "WTS-4KW-3P", (0x31, 0): "N/A", (0x30, 1): "WTS-5KW-3P", (0x31, 1): "N/A", (0x30, 2): "WTS-6KW-3P", (0x31, 2): "WTS-4.2KW-1P", (0x30, 3): "WTS-8KW-3P", (0x31, 3): "WTS-4.6KW-1P", (0x30, 4): "WTS-10KW-3P", (0x31, 4): "WTS-5KW-1P", (0x30, 5): "WTS-12KW-3P", (0x31, 5): "WTS-6KW-1P", (0x30, 6): "N/A", (0x31, 6): "WTS-7KW-1P", (0x30, 7): "N/A", (0x31, 7): "WTS-8KW-1P", (0x30, 8): "N/A", (0x31, 8): "WTS-3KW-1P", (0x30, 9): "N/A", (0x31, 9): "WTS-3.6KW-1P",}.get(((val >> 8), (val & 0xFF)), "Neznámé"), entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="Regulace sítě", key="grid_regulation", register=10104, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="Výkon na fázi A (Měřič)", key="phase_a_power_on_meter", register=10994, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Výkon na fázi B (Měřič)", key="phase_b_power_on_meter", register=10996, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Výkon na fázi C (Měřič)", key="phase_c_power_on_meter", register=10998, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Celkový výkon (Měřič)", key="total_power_on_meter", register=11000, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Sdružené napětí sítě A/B", key="grid_line_voltage_ab", register=11006, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Sdružené napětí sítě B/C", key="grid_line_voltage_bc", register=11007, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Sdružené napětí sítě C/A", key="grid_line_voltage_ca", register=11008, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Celková doba výroby z FV", key="total_pv_generation_time", register=11022, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfTime.HOURS, state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:timer-sand"),
    SunwayModbusSensorEntityDescription(name="Celková energie dodaná do sítě (Měřič)", key="total_grid_injection_energy", register=41102, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=0.1, rounding=1, icon="mdi:home-export-outline"),
    SunwayModbusSensorEntityDescription(name="Celková energie odebraná ze sítě (Měřič)", key="total_purchasing_energy", register=41104, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=0.1, rounding=1, icon="mdi:home-import-outline"),
    
    # --- OPRAVENÉ DENNÍ STATISTIKY S OCHRANOU PROTI ZÁPORNÝM HODNOTÁM ---
    # Používáme REGISTER_S16 + naši value_function ve scale [cite: 6, 16, 41]
    
    SunwayModbusSensorEntityDescription(name="Total PV Generation Today", key="total_pv_generation_today", register=41005, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=value_function_energy_no_negative, rounding=1),
    SunwayModbusSensorEntityDescription(name="Import Energy Today", key="day_grid_purchasing_energy", register=41001, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=value_function_energy_no_negative, rounding=1, icon="mdi:home-import-outline"),
    SunwayModbusSensorEntityDescription(name="Export Energy Today", key="day_grid_injection_energy", register=41000, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=value_function_energy_no_negative, rounding=1, icon="mdi:home-export-outline"),
    SunwayModbusSensorEntityDescription(name="Daily Load Consumption", key="day_loading_energy", register=41006, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=value_function_energy_no_negative, rounding=1, icon="mdi:home-lightning-bolt"),
    SunwayModbusSensorEntityDescription(name="Daily Battery Charge", key="day_battery_charge_energy", register=41003, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=value_function_energy_no_negative, rounding=1, icon="mdi:battery-arrow-up"),
    SunwayModbusSensorEntityDescription(name="Daily Battery Discharge", key="day_battery_discharge_energy", register=41004, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=value_function_energy_no_negative, rounding=1, icon="mdi:battery-arrow-down"),
    
    # --- OSTATNÍ SENZORY ---
    SunwayModbusSensorEntityDescription(name="Celková energie ze zálohy", key="total_backup_energy", register=41106, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=0.1, rounding=1, icon="mdi:battery-power"),
    SunwayModbusSensorEntityDescription(name="Celková energie nabitá do baterie", key="total_energy_charged_to_battery", register=41108, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=0.1, rounding=1, icon="mdi:battery-arrow-up"),
    SunwayModbusSensorEntityDescription(name="Celková energie vybitá z baterie", key="total_energy_discharged_from_battery", register=41110, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=0.1, rounding=1, icon="mdi:battery-arrow-down"),
    SunwayModbusSensorEntityDescription(name="Napětí fáze A sítě", key="grid_phase_a_voltage", register=11009, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud fáze A sítě", key="grid_phase_a_current", register=11010, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Napětí fáze B sítě", key="grid_phase_b_voltage", register=11011, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud fáze B sítě", key="grid_phase_b_current", register=11012, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Napětí fáze C sítě", key="grid_phase_c_voltage", register=11013, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud fáze C sítě", key="grid_phase_c_current", register=11014, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Frekvence sítě", key="grid_frequency", register=11015, native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, scale=0.01, rounding=2),
    SunwayModbusSensorEntityDescription(name="AC Výkon", key="ac_power", register=11016, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Celková výroba z FV od instalace", key="total_pv_generation_since_installation", register=11020, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Celkový vstupní výkon z FV", key="pv_input_total_power", register=11028, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Napětí PV1", key="pv1_voltage", register=11038, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud PV1", key="pv1_current", register=11039, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Vstupní výkon PV1", key="pv1_input_power", register=11062, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Napětí PV2", key="pv2_voltage", register=11040, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud PV2", key="pv2_current", register=11041, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Vstupní výkon PV2", key="pv2_input_power", register=11064, register_data_type=REGISTER_U32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Teplota Senzor 1", key="temperature_sensor_1", register=11032, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="Teplota Senzor 2", key="temperature_sensor_2", register=11033, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="Teplota Senzor 3", key="temperature_sensor_3", register=11034, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="Teplota Senzor 4", key="temperature_sensor_4", register=11035, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="Napětí zálohy A", key="backup_a_voltage", register=40200, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud zálohy A", key="backup_a_current", register=40201, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Výkon zálohy A", key="backup_a_power", register=40204, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Frekvence zálohy A", key="backup_a_frequency", register=40202, native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, scale=0.01, rounding=2),
    SunwayModbusSensorEntityDescription(name="Napětí zálohy B", key="backup_b_voltage", register=40210, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud zálohy B", key="backup_b_current", register=40211, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Frekvence zálohy B", key="backup_b_frequency", register=40212, native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, scale=0.01, rounding=2),
    SunwayModbusSensorEntityDescription(name="Výkon zálohy B", key="backup_b_power", register=40214, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, scale=1, rounding=0, state_class=SensorStateClass.MEASUREMENT),
    SunwayModbusSensorEntityDescription(name="Napětí zálohy C", key="backup_c_voltage", register=40220, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud zálohy C", key="backup_c_current", register=40221, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Frekvence zálohy C", key="backup_c_frequency", register=40222, native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, scale=0.01, rounding=2),
    SunwayModbusSensorEntityDescription(name="Výkon zálohy C", key="backup_c_power", register=40224, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, scale=1, rounding=0, state_class=SensorStateClass.MEASUREMENT),
    SunwayModbusSensorEntityDescription(name="Celkový výkon zálohy", key="total_backup_power", register=40230, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Aktivní výkon fáze A (Střídač)", key="inverter_phase_a_power", register=40236, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Aktivní výkon fáze B (Střídač)", key="inverter_phase_b_power", register=40242, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Aktivní výkon fáze C (Střídač)", key="inverter_phase_c_power", register=40248, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="Napětí baterie", key="battery_voltage", register=40254, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Proud baterie", key="battery_current", register=40255, register_data_type=REGISTER_S16, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=0.1, rounding=1),
    SunwayModbusSensorEntityDescription(name="Režim baterie", key="battery_mode", register=40256, scale={0: "Vybíjení", 1: "Nabíjení"}),
    SunwayModbusSensorEntityDescription(name="Výkon baterie", key="battery_power", register=40258, register_data_type=REGISTER_S32, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, scale=1, rounding=0),
    SunwayModbusSensorEntityDescription(name="SOC baterie", key="battery_soc", register=43000, native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT, scale=0.01, rounding=0),
    SunwayModbusSensorEntityDescription(name="SOH baterie", key="battery_soh", register=43001, native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, scale=0.01, rounding=0, icon="mdi:battery-heart", entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Typ baterie", key="bms_battery_type", register=42000, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Počet stringů baterie", key="bms_battery_strings", register=42001, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Protokol", key="bms_protocol", register=42002, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Verze softwaru", key="bms_software_version", register=42003, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Verze hardwaru", key="bms_hardware_version", register=42004, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Max. nabíjecí proud", key="bms_max_charge_current", register=42005, scale=0.1, rounding=1, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Max. vybíjecí proud", key="bms_max_discharge_current", register=42006, scale=0.1, rounding=1, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Status", key="bms_status", register=43002, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Teplota packu", key="bms_pack_temperature", register=43003, register_data_type=REGISTER_S16, scale=0.1, rounding=1, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Max. teplota článku", key="bms_max_cell_temperature", register=43009, register_data_type=REGISTER_S16, scale=0.1, rounding=1, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Min. teplota článku", key="bms_min_cell_temperature", register=43011, register_data_type=REGISTER_S16, scale=0.1, rounding=1, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Max. napětí článku", key="bms_max_cell_voltage", register=43013, scale=0.001, rounding=3, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Min. napětí článku", key="bms_min_cell_voltage", register=43015, scale=0.001, rounding=3, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, entity_category=EntityCategory.DIAGNOSTIC),
    SunwayModbusSensorEntityDescription(name="BMS Chybový kód (surová hodnota)", key="bms_error_code_raw", register=43016, register_data_type=REGISTER_U32, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:alert-box"),
    SunwayModbusSensorEntityDescription(name="BMS Varovný kód (surová hodnota)", key="bms_warning_code_raw", register=43018, register_data_type=REGISTER_U32, entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:alert"),
]

# ============================ plugin declaration =================================================

@dataclass(kw_only=True)
class sunway_plugin(plugin_base):

    def isAwake(self, datadict):
        """Určuje, zda je střídač v aktivním stavu."""
        return True

    async def async_determineInverterType(self, hub, configdict):
        _LOGGER.info(f"{hub.name}: zkouším určit typ střídače SunWay")

        try:
            inverter_data = await hub.async_read_holding_registers(unit=hub._modbus_addr, address=10000, count=4)
        except Exception as ex:
            _LOGGER.error(f"{hub.name}: chyba při čtení sériového čísla: {ex}")
            return 0

        if inverter_data is None or inverter_data.isError():
            _LOGGER.error(f"{hub.name}: nelze přečíst sériové číslo z adresy 10000.")
            return 0
        
        raw = convert_from_registers(inverter_data.registers, DataType.STRING, "big")
        
        if isinstance(raw, (bytes, bytearray)):
            seriesnumber = raw.decode("ascii", errors="ignore").strip()
        else:
            seriesnumber = str(raw).strip()
            
        hub.seriesnumber = seriesnumber
        _LOGGER.info(f"{hub.name}: Sériové číslo střídače: {seriesnumber}")

        if seriesnumber:
            self.inverter_model = "STT-10KTL"
            return SUNWAY_STT_10KTL
        else:
            _LOGGER.error(f"{hub.name}: nelze určit typ střídače, sériové číslo je prázdné.")
            return 0

    def matchInverterWithMask(self, inverterspec, entitymask, serialnumber="not relevant", blacklist=None):
        return (inverterspec & entitymask) != 0

    def getSoftwareVersion(self, new_data):
        raw_version = new_data.get("firmware_version")
        if raw_version is not None:
             return str(raw_version)
        return None

    def getHardwareVersion(self, new_data):
        return None

# Finální inicializace s povinným TIME_TYPES pro jádro pluginu
plugin_instance = sunway_plugin(
    plugin_name="SunWay",
    plugin_manufacturer="SunWay",
    SENSOR_TYPES=SENSOR_TYPES,
    NUMBER_TYPES=NUMBER_TYPES,
    BUTTON_TYPES=BUTTON_TYPES,
    SELECT_TYPES=SELECT_TYPES,
    SWITCH_TYPES=SWITCH_TYPES,
    TIME_TYPES=[],
    block_size=100,
    order32="big",
    auto_block_ignore_readerror=True,
    default_holding_scangroup=SCAN_GROUP_MEDIUM,
    default_input_scangroup=SCAN_GROUP_AUTO,
    auto_default_scangroup=SCAN_GROUP_FAST,
    auto_slow_scangroup=SCAN_GROUP_MEDIUM,
)