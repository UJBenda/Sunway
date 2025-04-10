# custom_components/sunway_fve/const.py
import logging
from dataclasses import dataclass, KW_ONLY
from typing import Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    PERCENTAGE,
    UnitOfTime,
    POWER_VOLT_AMPERE_REACTIVE,
)

DOMAIN = "sunway_fve"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
# DEFAULT_SCAN_INTERVAL už nepotřebujeme globálně

# === NOVÉ: Definice skenovacích skupin ===
SCAN_GROUP_REALTIME = "realtime" # Pro rychle se měnící hodnoty (V, A, W, Hz) - např. 30s
SCAN_GROUP_DAILY_TOTALS = "daily" # Pro denní součty energie, stavové registry - např. 120s
SCAN_GROUP_LIFETIME_TOTALS = "totals" # Pro celkové součty energie - např. 600s
SCAN_GROUP_INFO = "info" # Pro statické informace (SN, FW) - např. 3600s
# === KONEC NOVÉ ČÁSTI ===

# --- Definice Dataclass pro Popis Senzoru ---
@dataclass
class SunwayModbusSensorEntityDescription(SensorEntityDescription):
    _: KW_ONLY
    register_address: int
    register_count: int
    data_type: str
    scale: float = 1.0
    read_only: bool = True
    register_type: str = "holding"
    scan_group: str = SCAN_GROUP_REALTIME # <-- PŘIDÁNO pole, výchozí je realtime

# --- Seznam Definovaných Senzorů ---
# Nyní s přiřazenou 'scan_group' pro každý senzor
SENSOR_DESCRIPTIONS: list[SunwayModbusSensorEntityDescription] = [
    # === Blok 10000+ ===
    SunwayModbusSensorEntityDescription(
        key="inverter_sn", name="Inverter Serial Number",
        register_address=10000, register_count=8, data_type="STR", read_only=True, register_type="holding", scan_group=SCAN_GROUP_INFO,
    ),
    SunwayModbusSensorEntityDescription(
        key="firmware_version", name="Firmware Version",
        register_address=10011, register_count=2, data_type="U32", read_only=True, register_type="holding", scan_group=SCAN_GROUP_INFO,
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_regulation", name="Grid Regulation Status",
        register_address=10104, register_count=1, data_type="U16", read_only=True, register_type="holding", scan_group=SCAN_GROUP_DAILY_TOTALS, # Stav se nemění moc často
    ),
    SunwayModbusSensorEntityDescription(
        key="running_status", name="Inverter Running Status",
        register_address=10105, register_count=1, data_type="U16", read_only=True, register_type="holding", scan_group=SCAN_GROUP_DAILY_TOTALS, # Stav se nemění moc často
    ),
    SunwayModbusSensorEntityDescription(
        key="fault_flag1", name="Fault FLAG1",
        register_address=10112, register_count=2, data_type="U32", read_only=True, register_type="holding", scan_group=SCAN_GROUP_DAILY_TOTALS, # TODO: Needs parsing
    ),
    SunwayModbusSensorEntityDescription(
        key="phase_a_power_on_meter", name="Phase A Power on Meter", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=10114, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="phase_b_power_on_meter", name="Phase B Power on Meter", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=10116, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="phase_c_power_on_meter", name="Phase C Power on Meter", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=10118, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_power_on_meter", name="Total Power on Meter", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=10120, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_grid_injection_energy_meter", name="Total Grid-Injection Energy on Meter", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=2,
        register_address=10994, register_count=2, data_type="U32", scale=100.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS, # Celkový součet
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_purchased_grid_meter", name="Total Energy Purchased from Grid on Meter", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=2,
        register_address=10996, register_count=2, data_type="U32", scale=100.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS, # Celkový součet
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_line_ab_voltage", name="Grid Lines A-B Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=10998, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_line_bc_voltage", name="Grid Lines B-C Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=10999, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_line_ca_voltage", name="Grid Lines C-A Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11000, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_a_voltage", name="Grid Phase A Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11001, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="grid_phase_a_current", name="Grid Phase A Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11002, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_b_voltage", name="Grid Phase B Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11003, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_b_current", name="Grid Phase B Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11004, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_c_voltage", name="Grid Phase C Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11005, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_c_current", name="Grid Phase C Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11006, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="grid_frequency", name="Grid Frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=11007, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="power_ac", name="AC Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=11008, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="pv_gen_today", name="PV Generation Today", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=11010, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS, # Denní součet
    ),
     SunwayModbusSensorEntityDescription(
        key="pv_gen_total", name="PV Generation Total", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=11012, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS, # Celkový součet
    ),
    SunwayModbusSensorEntityDescription(
        key="pv_gen_time_total", name="PV Generation Time Total", native_unit_of_measurement=UnitOfTime.HOURS, state_class=SensorStateClass.TOTAL_INCREASING,
        register_address=11014, register_count=2, data_type="U32", scale=1.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS, # Celkový součet
    ),
     SunwayModbusSensorEntityDescription(
        key="pv_total_power", name="PV Input Total Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=11016, register_count=2, data_type="U32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_1", name="Temperature Sensor 1", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11018, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_2", name="Temperature Sensor 2", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11019, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_3", name="Temperature Sensor 3", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11020, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_4", name="Temperature Sensor 4", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11021, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="pv1_voltage", name="PV1 Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11028, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="pv1_current", name="PV1 Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11029, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", scan_group=SCAN_GROUP_REALTIME, # OPRAVENO
    ),
    SunwayModbusSensorEntityDescription(
        key="pv2_voltage", name="PV2 Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11030, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="pv2_current", name="PV2 Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11031, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME, # Odhad: input
    ),
    SunwayModbusSensorEntityDescription(
        key="pv1_input_power", name="PV1 Input Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=11032, register_count=2, data_type="U32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="pv2_input_power", name="PV2 Input Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=11034, register_count=2, data_type="U32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="arm_fault_flag1", name="ARM Fault FLAG1",
        register_address=11036, register_count=2, data_type="U32", read_only=True, register_type="holding", scan_group=SCAN_GROUP_DAILY_TOTALS, # TODO: Needs parsing
    ),

    # === Blok 4xxxx (Backup, Battery, Energy totals) ===
    SunwayModbusSensorEntityDescription(
        key="backup_a_v", name="Backup Phase A Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40200, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_a_i", name="Backup Phase A Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40201, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_a_f", name="Backup Phase A Frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=40202, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_a_p", name="Backup Phase A Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40204, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_b_v", name="Backup Phase B Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40210, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_b_i", name="Backup Phase B Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40211, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_b_f", name="Backup Phase B Frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=40212, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_b_p", name="Backup Phase B Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40214, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_c_v", name="Backup Phase C Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40220, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_c_i", name="Backup Phase C Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40221, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_c_f", name="Backup Phase C Frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=40222, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_c_p", name="Backup Phase C Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40224, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_backup_p", name="Total Backup Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40230, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="invt_a_p", name="Inverter Phase A Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40236, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="invt_b_p", name="Inverter Phase B Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40242, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="invt_c_p", name="Inverter Phase C Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40248, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_v", name="Battery Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40254, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="battery_current", name="Battery Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40255, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_mode", name="Battery Mode", # 0:discharge, 1:charge
        register_address=40256, register_count=1, data_type="U16", scale=1.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS, # TODO: Needs mapping
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_power", name="Battery Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40258, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),

    # === Blok 41xxx ===
    SunwayModbusSensorEntityDescription(
        key="energy_grid_injection_today", name="Energy Grid Injection Today", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41000, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_grid_purchase_today", name="Energy Grid Purchase Today", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41001, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_backup_output_today", name="Energy Backup Output Today", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41002, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_battery_charge_today", name="Energy Battery Charge Today", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41003, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_battery_discharge_today", name="Energy Battery Discharge Today", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41004, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_loading_today", name="Loading Energy Today", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41006, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_injected_grid", name="Total Energy Injected to Grid", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41102, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_purchased_grid_meter_alt", name="Total Energy Purchased from Grid from Meter Alt", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41104, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_backup_output", name="Total Backup Output Energy", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41106, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_battery_charge", name="Total Energy Charged to Battery", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41108, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_battery_discharge", name="Total Energy Discharged from Battery", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41110, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_loading_energy_grid_side", name="Total Loading Energy Consumed (Grid Side)", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41114, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS,
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_purchased_inverter_side", name="Total Energy Purchased (Inverter Side)", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41118, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_LIFETIME_TOTALS,
    ),

    # === Blok 42xxx ===
    SunwayModbusSensorEntityDescription(
        key="battery_types", name="Battery Types",
        register_address=42000, register_count=1, data_type="U16", read_only=True, register_type="holding", scan_group=SCAN_GROUP_INFO,
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_strings", name="Battery Strings",
        register_address=42001, register_count=1, data_type="U16", read_only=True, register_type="holding", scan_group=SCAN_GROUP_INFO,
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_protocol", name="Battery Protocol",
        register_address=42002, register_count=1, data_type="U16", read_only=True, register_type="holding", scan_group=SCAN_GROUP_INFO,
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_software_version", name="BMS Software Version",
        register_address=42003, register_count=1, data_type="U16", read_only=True, register_type="holding", scan_group=SCAN_GROUP_INFO,
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_hardware_version", name="BMS Hardware Version",
        register_address=42004, register_count=1, data_type="U16", read_only=True, register_type="holding", scan_group=SCAN_GROUP_INFO,
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_charge_imax", name="BMS Charge Imax", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=42005, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS, # Limit se nemění moc často
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_discharge_imax", name="BMS Discharge Imax", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=42006, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS, # Limit se nemění moc často
    ),

    # === Blok 43xxx ===
    SunwayModbusSensorEntityDescription(
        key="battery_soc", name="Battery SOC", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=43000, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_soh", name="Battery SOH", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=43001, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS, # Nemění se často
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_status", name="BMS Status",
        register_address=43002, register_count=1, data_type="U16", read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS, # TODO: Needs mapping
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_pack_temp", name="BMS Pack Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=43003, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_max_cell_temp_id", name="BMS Max Cell Temperature ID",
        register_address=43008, register_count=1, data_type="U16", read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_max_cell_temp", name="BMS Max Cell Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=43009, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_min_cell_temp_id", name="BMS Min Cell Temperature ID",
        register_address=43010, register_count=1, data_type="U16", read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_min_cell_temp", name="BMS Min Cell Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=43011, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_max_cell_volt_id", name="BMS Max Cell Voltage ID",
        register_address=43012, register_count=1, data_type="U16", read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_max_cell_volt", name="BMS Max Cell Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=43013, register_count=1, data_type="U16", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_min_cell_volt_id", name="BMS Min Cell Voltage ID",
        register_address=43014, register_count=1, data_type="U16", read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_min_cell_volt", name="BMS Min Cell Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=43015, register_count=1, data_type="U16", scale=1000.0, read_only=True, register_type="input", scan_group=SCAN_GROUP_REALTIME,
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_error_code", name="BMS ERROR CODE",
        register_address=43016, register_count=2, data_type="U32", read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS, # TODO: Needs parsing
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_warn_code", name="BMS WARN CODE",
        register_address=43018, register_count=2, data_type="U32", read_only=True, register_type="input", scan_group=SCAN_GROUP_DAILY_TOTALS, # TODO: Needs parsing
    ),
]

# --- Definice pro Ovládací Prvky ---
# Přidán scan_group, typicky realtime pro zobrazení aktuálního stavu
RW_REGISTER_MAP = {
    "grid_injection_limit_switch": {
        "address": 25100, "type": "switch", "write_map": {True: 1, False: 0},
        "data_type": "U16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
    },
    "grid_injection_limit_setting": {
        "address": 25103, "type": "number", "scale": 0.1, "unit": PERCENTAGE,
        "min_value": 0.0, "max_value": 100.0, "step": 0.1, "data_type": "U16", "count": 1,
        "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
    },
    "eps_ups_switch": {
        "address": 50001, "type": "switch", "write_map": {True: 1, False: 0},
         "data_type": "U16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "off_grid_voltage": {
         "address": 50004, "type": "number", "scale": 10.0, "unit": UnitOfElectricPotential.VOLT,
         "data_type": "U16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "off_grid_frequency": {
         "address": 50005, "type": "number", "scale": 100.0, "unit": UnitOfFrequency.HERTZ,
         "min_value": 45.00, "max_value": 65.00, "step": 0.01, "data_type": "U16", "count": 1,
         "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "hybrid_working_mode": { # TODO: Needs table 3.6 for options; implement as SELECT entity
         "address": 50000, "type": "select", "data_type": "U16", "count": 1, "register_type": "holding",
         "scan_group": SCAN_GROUP_DAILY_TOTALS # Nemění se často
         # TODO: Needs mapping
     },
     "off_grid_asymmetric_switch": {
         "address": 50006, "type": "switch", "write_map": {True: 1, False: 0},
         "data_type": "U16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "peak_load_shifting_switch": {
         "address": 50007, "type": "switch", "write_map": {True: 1, False: 0},
         "data_type": "U16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "max_grid_power_setting": { # TODO: Verify unit is kVA and scale 10?
         "address": 50009, "type": "number", "scale": 10.0, "unit": "kVA",
         "data_type": "U16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "inverter_ac_power_setting_mode": { # Registr 50202
        "address": 50202, "type": "select", "data_type": "U16", "count": 1, "register_type": "holding",
        "scan_group": SCAN_GROUP_REALTIME
        # TODO: Needs options mapping {0: "Off", 1: "Total", 2: "Per Phase"}
     },
     "total_ac_power_setting": {
         "address": 50203, "type": "number", "scale": 100.0, "unit": UnitOfPower.KILO_WATT,
         "data_type": "I16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "phase_a_power_setting": {
         "address": 50204, "type": "number", "scale": 100.0, "unit": UnitOfPower.KILO_WATT,
         "data_type": "I16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "phase_b_power_setting": {
         "address": 50205, "type": "number", "scale": 100.0, "unit": UnitOfPower.KILO_WATT,
         "data_type": "I16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "phase_c_power_setting": {
         "address": 50206, "type": "number", "scale": 100.0, "unit": UnitOfPower.KILO_WATT,
         "data_type": "I16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME
     },
     "battery_power_setting": {
         "address": 50207, "type": "number", "scale": 100.0, "unit": UnitOfPower.KILO_WATT, # Odhad!
         "data_type": "I16", "count": 1, "register_type": "holding", "scan_group": SCAN_GROUP_REALTIME # Odhad!
     },
}