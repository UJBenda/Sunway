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
    POWER_VOLT_AMPERE_REACTIVE, # Pro kVA
)

DOMAIN = "sunway_fve"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 60 # Sekundy

# --- Definice Dataclass pro Popis Senzoru ---
@dataclass
class SunwayModbusSensorEntityDescription(SensorEntityDescription):
    _: KW_ONLY
    register_address: int
    register_count: int
    data_type: str
    scale: float = 1.0
    read_only: bool = True
    register_type: str = "holding" # Výchozí typ je holding

# --- Seznam Definovaných Senzorů ---
# register_type = 'input' (odhad pro RO měření)
# register_type = 'holding' (odhad pro RW a RO stav/info/konfiguraci)
SENSOR_DESCRIPTIONS: list[SunwayModbusSensorEntityDescription] = [
    # === Blok 10000+ (Info, Status, Základní měření) ===
    SunwayModbusSensorEntityDescription(
        key="inverter_sn", name="Inverter Serial Number",
        register_address=10000, register_count=8, data_type="STR", read_only=True, register_type="holding",
    ),
    # TODO: 10008 Equipment Info - vyžaduje tabulku 3.2 pro interpretaci
    # SunwayModbusSensorEntityDescription(key="equipment_info", name="Equipment Info", register_address=10008, register_count=1, data_type="U16", read_only=True, register_type="holding"),
    SunwayModbusSensorEntityDescription(
        key="firmware_version", name="Firmware Version", # Zobrazí číslo, může vyžadovat formátování
        register_address=10011, register_count=2, data_type="U32", read_only=True, register_type="holding",
    ),
    # TODO: 10100-10102 Datum/Čas - vyžaduje speciální parsování
    SunwayModbusSensorEntityDescription(
        key="grid_regulation", name="Grid Regulation Status", # 0:wait, 1:check
        register_address=10104, register_count=1, data_type="U16", read_only=True, register_type="holding", # TODO: Needs mapping
    ),
    SunwayModbusSensorEntityDescription(
        key="running_status", name="Inverter Running Status", # 2:OnGrid, 3:Fault, 4:Flash, 5:OffGrid
        register_address=10105, register_count=1, data_type="U16", read_only=True, register_type="holding", # TODO: Needs mapping
    ),
    SunwayModbusSensorEntityDescription(
        key="fault_flag1", name="Fault FLAG1", # Zobrazí číslo, vyžaduje tabulku 3.3/parsování bitů
        register_address=10112, register_count=2, data_type="U32", read_only=True, register_type="holding", # TODO: Needs parsing
    ),
    SunwayModbusSensorEntityDescription(
        key="phase_a_power_on_meter", name="Phase A Power on Meter",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=10114, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="phase_b_power_on_meter", name="Phase B Power on Meter",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=10116, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="phase_c_power_on_meter", name="Phase C Power on Meter",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=10118, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="total_power_on_meter", name="Total Power on Meter",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=10120, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="total_grid_injection_energy_meter", name="Total Grid-Injection Energy on Meter",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=2,
        register_address=10994, register_count=2, data_type="U32", scale=100.0, read_only=True, register_type="input", # Měření (Energy Dashboard - Export)
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_purchased_grid_meter", name="Total Energy Purchased from Grid on Meter", # Přejmenováno pro odlišení
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=2,
        register_address=10996, register_count=2, data_type="U32", scale=100.0, read_only=True, register_type="input", # Měření (Energy Dashboard - Import)
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_line_ab_voltage", name="Grid Lines A-B Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=10998, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření (ale asi holding?) Zkusíme input.
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_line_bc_voltage", name="Grid Lines B-C Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=10999, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření (ale asi holding?) Zkusíme input.
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_line_ca_voltage", name="Grid Lines C-A Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11000, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření (ale asi holding?) Zkusíme input.
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_a_voltage", name="Grid Phase A Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11001, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", # Ukázalo se, že je holding
    ),
     SunwayModbusSensorEntityDescription(
        key="grid_phase_a_current", name="Grid Phase A Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11002, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", # Odhad holding
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_b_voltage", name="Grid Phase B Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11003, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", # Ukázalo se, že je holding
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_b_current", name="Grid Phase B Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11004, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", # Odhad holding
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_c_voltage", name="Grid Phase C Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11005, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", # Ukázalo se, že je holding
    ),
    SunwayModbusSensorEntityDescription(
        key="grid_phase_c_current", name="Grid Phase C Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11006, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", # Odhad holding
    ),
     SunwayModbusSensorEntityDescription(
        key="grid_frequency", name="Grid Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=11007, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="power_ac", name="AC Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=11008, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="pv_gen_today", name="PV Generation Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=11010, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření
    ),
     SunwayModbusSensorEntityDescription(
        key="pv_gen_total", name="PV Generation Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=11012, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="pv_gen_time_total", name="PV Generation Time Total",
        native_unit_of_measurement=UnitOfTime.HOURS, state_class=SensorStateClass.TOTAL_INCREASING,
        register_address=11014, register_count=2, data_type="U32", scale=1.0, read_only=True, register_type="input", # Měření
    ),
     SunwayModbusSensorEntityDescription(
        key="pv_total_power", name="PV Input Total Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=11016, register_count=2, data_type="U32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_1", name="Temperature Sensor 1",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11018, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_2", name="Temperature Sensor 2",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11019, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_3", name="Temperature Sensor 3",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11020, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="temp_sensor_4", name="Temperature Sensor 4",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11021, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="pv1_voltage", name="PV1 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11028, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
     SunwayModbusSensorEntityDescription(
        key="pv1_current", name="PV1 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11029, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="holding", # Ukázalo se, že je holding
    ),
    SunwayModbusSensorEntityDescription(
        key="pv2_voltage", name="PV2 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11030, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="pv2_current", name="PV2 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=11031, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Odhad: input (jako PV1 V)
    ),
    SunwayModbusSensorEntityDescription(
        key="pv1_input_power", name="PV1 Input Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=11032, register_count=2, data_type="U32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="pv2_input_power", name="PV2 Input Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=11034, register_count=2, data_type="U32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="arm_fault_flag1", name="ARM Fault FLAG1", # Zobrazí číslo, vyžaduje tabulku 3.3/parsování bitů
        register_address=11036, register_count=2, data_type="U32", read_only=True, register_type="holding", # Odhad: holding (stav) # TODO: Needs parsing
    ),

    # === Blok 2xxxx (RW Registry - viz RW_REGISTER_MAP) ===
    # 20000-20002 RTC - přeskočeno
    # 25100 Grid Injection Limit Switch - definováno v RW_REGISTER_MAP
    # 25103 Grid Injection Limit Setting - definováno v RW_REGISTER_MAP
    # 25104 Smart Meter COM. Status - WO - přeskočeno
    # 25105 Phase A Power On Meter - WO - přeskočeno
    # 25107 Phase B Power On Meter - WO - přeskočeno
    # 25109 Phase C Power On Meter - WO - přeskočeno

    # === Blok 4xxxx (Backup, Battery, Energy totals) ===
    SunwayModbusSensorEntityDescription(
        key="backup_a_v", name="Backup Phase A Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40200, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_a_i", name="Backup Phase A Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40201, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_a_f", name="Backup Phase A Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=40202, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_a_p", name="Backup Phase A Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40204, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_b_v", name="Backup Phase B Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40210, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_b_i", name="Backup Phase B Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40211, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_b_f", name="Backup Phase B Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=40212, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_b_p", name="Backup Phase B Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40214, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_c_v", name="Backup Phase C Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40220, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_c_i", name="Backup Phase C Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40221, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_c_f", name="Backup Phase C Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=40222, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="backup_c_p", name="Backup Phase C Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40224, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="total_backup_p", name="Total Backup Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40230, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="invt_a_p", name="Inverter Phase A Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40236, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="invt_b_p", name="Inverter Phase B Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40242, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="invt_c_p", name="Inverter Phase C Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40248, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_v", name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40254, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
     SunwayModbusSensorEntityDescription(
        key="battery_current", name="Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=40255, register_count=1, data_type="I16", scale=10.0, read_only=True, register_type="input", # Měření (necháváme input)
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_mode", name="Battery Mode", # 0:discharge, 1:charge
        register_address=40256, register_count=1, data_type="U16", scale=1.0, read_only=True, register_type="input", # Odhad: input (stav BMS?) # TODO: Needs mapping
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_power", name="Battery Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=40258, register_count=2, data_type="I32", scale=1000.0, read_only=True, register_type="input", # Měření
    ),

    # === Blok 41xxx (Energy totals - Day & Lifetime) ===
    SunwayModbusSensorEntityDescription(
        key="energy_grid_injection_today", name="Energy Grid Injection Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41000, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_grid_purchase_today", name="Energy Grid Purchase Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41001, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_backup_output_today", name="Energy Backup Output Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41002, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_battery_charge_today", name="Energy Battery Charge Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41003, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="energy_battery_discharge_today", name="Energy Battery Discharge Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41004, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    # 41005 je stejné jako 11010 ? Přeskakuji prozatím
    # SunwayModbusSensorEntityDescription(key="energy_pv_generation_today_alt", name="Energy PV Generation Today Alt", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, register_address=41005, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input"),
    SunwayModbusSensorEntityDescription(
        key="energy_loading_today", name="Loading Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41006, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    # 41008 je zdvojené s 41001 ? Přeskakuji
    # SunwayModbusSensorEntityDescription(key="energy_purchased_grid_today_alt", name="Energy Purchased from Grid Today Alt", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, register_address=41008, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input"),

    SunwayModbusSensorEntityDescription(
        key="total_energy_injected_grid", name="Total Energy Injected to Grid",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41102, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření (Energy Dashboard - Export Alt?)
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_purchased_grid_meter_alt", name="Total Energy Purchased from Grid from Meter Alt", # Alt. k 10996
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41104, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření (Energy Dashboard - Import Alt?)
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_backup_output", name="Total Backup Output Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41106, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_battery_charge", name="Total Energy Charged to Battery",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41108, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření (Energy Dashboard - Batt Charge)
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_battery_discharge", name="Total Energy Discharged from Battery",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41110, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření (Energy Dashboard - Batt Discharge)
    ),
    # 41112 je stejné jako 11012 ? Přeskakuji
    # SunwayModbusSensorEntityDescription(key="total_pv_generation_alt", name="Total PV Generation Alt", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, register_address=41112, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input"),
    SunwayModbusSensorEntityDescription(
        key="total_loading_energy_grid_side", name="Total Loading Energy Consumed (Grid Side)",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41114, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="total_energy_purchased_inverter_side", name="Total Energy Purchased (Inverter Side)", # Alt. k 10996/41104
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
        register_address=41118, register_count=2, data_type="U32", scale=10.0, read_only=True, register_type="input", # Měření
    ),

    # === Blok 42xxx (Battery Info) ===
    # Tyto jsou spíše informační, můžeme je přidat, ale nemusí být užitečné bez kontextu
    SunwayModbusSensorEntityDescription(
        key="battery_types", name="Battery Types", # Číselný kód typu
        register_address=42000, register_count=1, data_type="U16", read_only=True, register_type="holding", # Odhad: holding (info)
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_strings", name="Battery Strings", # Počet stringů?
        register_address=42001, register_count=1, data_type="U16", read_only=True, register_type="holding", # Odhad: holding (info)
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_protocol", name="Battery Protocol", # Číselný kód protokolu
        register_address=42002, register_count=1, data_type="U16", read_only=True, register_type="holding", # Odhad: holding (info)
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_software_version", name="BMS Software Version", # Formát?
        register_address=42003, register_count=1, data_type="U16", read_only=True, register_type="holding", # Odhad: holding (info)
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_hardware_version", name="BMS Hardware Version", # Formát?
        register_address=42004, register_count=1, data_type="U16", read_only=True, register_type="holding", # Odhad: holding (info)
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_charge_imax", name="BMS Charge Imax",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=42005, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření/Limit -> input?
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_discharge_imax", name="BMS Discharge Imax",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=42006, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření/Limit -> input?
    ),

    # === Blok 43xxx (BMS Data) ===
    SunwayModbusSensorEntityDescription(
        key="battery_soc", name="Battery SOC",
        native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        register_address=43000, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="battery_soh", name="Battery SOH",
        native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2, # Není standardní device_class
        register_address=43001, register_count=1, data_type="U16", scale=100.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_status", name="BMS Status", # Vyžaduje mapování
        register_address=43002, register_count=1, data_type="U16", read_only=True, register_type="input", # Odhad: input (stav BMS) # TODO: Needs mapping
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_pack_temp", name="BMS Pack Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=43003, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_max_cell_temp_id", name="BMS Max Cell Temperature ID",
        register_address=43008, register_count=1, data_type="U16", read_only=True, register_type="input", # Měření/Info
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_max_cell_temp", name="BMS Max Cell Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=43009, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_min_cell_temp_id", name="BMS Min Cell Temperature ID",
        register_address=43010, register_count=1, data_type="U16", read_only=True, register_type="input", # Měření/Info
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_min_cell_temp", name="BMS Min Cell Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
        register_address=43011, register_count=1, data_type="U16", scale=10.0, read_only=True, register_type="input", # Měření
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_max_cell_volt_id", name="BMS Max Cell Voltage ID",
        register_address=43012, register_count=1, data_type="U16", read_only=True, register_type="input", # Měření/Info
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_max_cell_volt", name="BMS Max Cell Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=43013, register_count=1, data_type="U16", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_min_cell_volt_id", name="BMS Min Cell Voltage ID",
        register_address=43014, register_count=1, data_type="U16", read_only=True, register_type="input", # Měření/Info
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_min_cell_volt", name="BMS Min Cell Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3,
        register_address=43015, register_count=1, data_type="U16", scale=1000.0, read_only=True, register_type="input", # Měření
    ),
    SunwayModbusSensorEntityDescription(
        key="bms_error_code", name="BMS ERROR CODE", # Zobrazí číslo, vyžaduje parsování bitů/mapování
        register_address=43016, register_count=2, data_type="U32", read_only=True, register_type="input", # Odhad: input (stav BMS) # TODO: Needs parsing
    ),
     SunwayModbusSensorEntityDescription(
        key="bms_warn_code", name="BMS WARN CODE", # Zobrazí číslo, vyžaduje parsování bitů/mapování
        register_address=43018, register_count=2, data_type="U32", read_only=True, register_type="input", # Odhad: input (stav BMS) # TODO: Needs parsing
    ),

    # === Blok 5xxxx (RW Registry - viz RW_REGISTER_MAP) ===
    # 50000 Hybrid Inverter Working Mode Setting - nutno přidat do RW_REGISTER_MAP (typ select?) # TODO: Needs table 3.6
    # 50001 EPS/UPS function Switch - definováno v RW_REGISTER_MAP
    # 50004 Off-grid Voltage Setting - definováno v RW_REGISTER_MAP
    # 50005 Off-grid Frequency Setting - definováno v RW_REGISTER_MAP
    # 50006 Off-grid asymmetric output function switch - nutno přidat do RW_REGISTER_MAP (typ switch)
    # 50007 Peak Load Shifting Switch - nutno přidat do RW_REGISTER_MAP (typ switch)
    # 50009 Max. Grid Power Value Setting - nutno přidat do RW_REGISTER_MAP (typ number, unit kVA?)
    # 50202-50207 Power Settings - nutno přidat do RW_REGISTER_MAP (typ number/select?)

]

# --- Definice pro Ovládací Prvky (s doplněným register_type) ---
RW_REGISTER_MAP = {
    "grid_injection_limit_switch": {
        "address": 25100, "type": "switch", "write_map": {True: 1, False: 0},
        "data_type": "U16", "count": 1, "register_type": "holding"
    },
    "grid_injection_limit_setting": {
        "address": 25103, "type": "number", "scale": 0.1, "unit": PERCENTAGE,
        "min_value": 0.0, "max_value": 100.0, "step": 0.1, "data_type": "U16", "count": 1,
        "register_type": "holding"
    },
    "eps_ups_switch": {
        "address": 50001, "type": "switch", "write_map": {True: 1, False: 0},
         "data_type": "U16", "count": 1, "register_type": "holding"
     },
     "off_grid_voltage": {
         "address": 50004, "type": "number", "scale": 10.0, "unit": UnitOfElectricPotential.VOLT,
         "data_type": "U16", "count": 1, "register_type": "holding",
         # TODO: Zjistit min/max/step z dokumentace Sunway
     },
     "off_grid_frequency": {
         "address": 50005, "type": "number", "scale": 100.0, "unit": UnitOfFrequency.HERTZ,
         "min_value": 45.00, "max_value": 65.00, "step": 0.01, "data_type": "U16", "count": 1,
         "register_type": "holding"
     },
     # === Zde přidejte definice pro další RW registry ===
     "hybrid_working_mode": { # TODO: Needs table 3.6 for options; implement as SELECT entity
         "address": 50000, "type": "select", "data_type": "U16", "count": 1, "register_type": "holding"
     },
     "off_grid_asymmetric_switch": {
         "address": 50006, "type": "switch", "write_map": {True: 1, False: 0},
         "data_type": "U16", "count": 1, "register_type": "holding"
     },
     "peak_load_shifting_switch": {
         "address": 50007, "type": "switch", "write_map": {True: 1, False: 0},
         "data_type": "U16", "count": 1, "register_type": "holding"
     },
     "max_grid_power_setting": { # TODO: Verify unit is kVA and scale 10?
         "address": 50009, "type": "number", "scale": 10.0, "unit": "kVA", # POWER_VOLT_AMPERE? Needs testing
         "data_type": "U16", "count": 1, "register_type": "holding"
     },
     # TODO: Power settings 50202-50207 require more complex logic based on 50202 value.
     # Implement as combination of select (for 50202) and numbers, potentially.
}