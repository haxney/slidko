# I²C address → part-name lookup table (committed data as per design.md)
_ADDRESS_BOOK = {
    0x68: [
        {"part": "MPU-6050", "kind": "IMU", "note": "Common IMU default address"},
        {"part": "MPU-9250", "kind": "IMU", "note": "Common IMU default address"},
        {"part": "ICM-20602", "kind": "IMU", "note": "Common IMU default address"},
        {"part": "DS3231", "kind": "RTC", "note": "Real-time clock"},
        {"part": "DS1307", "kind": "RTC", "note": "Real-time clock"},
    ],
    0x69: [
        {"part": "MPU-6050", "kind": "IMU", "note": "Common IMU default address"},
        {"part": "MPU-9250", "kind": "IMU", "note": "Common IMU default address"},
        {"part": "ICM-20602", "kind": "IMU", "note": "Common IMU default address"},
    ],
    0x76: [
        {"part": "BMP280", "kind": "Barometer", "note": "Barometric pressure sensor"},
        {"part": "BME280", "kind": "Barometer", "note": "Barometric pressure sensor"},
    ],
    0x77: [
        {"part": "BMP280", "kind": "Barometer", "note": "Barometric pressure sensor"},
        {"part": "BME280", "kind": "Barometer", "note": "Barometric pressure sensor"},
        {"part": "BMP180", "kind": "Barometer", "note": "Barometric pressure sensor"},
    ],
    0x0C: [
        {"part": "AK8963", "kind": "Magnetometer", "note": "Auxiliary magnetometer"},
    ],
    0x0D: [
        {"part": "AK8963", "kind": "Magnetometer", "note": "Auxiliary magnetometer"},
        {"part": "QMC5883L", "kind": "Magnetometer", "note": "Magnetometer"},
    ],
    0x1E: [{"part": "HMC5883L", "kind": "Magnetometer", "note": "Magnetometer"}],
    0x29: [
        {
            "part": "VL53L0X",
            "kind": "ToF distance sensor",
            "note": "Time-of-Flight distance sensor",
        }
    ],
    0x3C: [
        {"part": "SSD1306", "kind": "Display", "note": "OLED display"},
        {"part": "SH1106", "kind": "Display", "note": "OLED display"},
    ],
    0x3D: [
        {"part": "SSD1306", "kind": "Display", "note": "OLED display"},
        {"part": "SH1106", "kind": "Display", "note": "OLED display"},
    ],
    0x40: [
        {"part": "INA219", "kind": "Current sensor", "note": "Current/power monitor"},
        {"part": "INA226", "kind": "Current sensor", "note": "Current/power monitor"},
        {
            "part": "PCA9685",
            "kind": "PWM/servo driver",
            "note": "16-channel PWM controller",
        },
        {
            "part": "Si7021",
            "kind": "Humidity sensor",
            "note": "Humidity/temperature sensor",
        },
    ],
    0x41: [
        {"part": "INA219", "kind": "Current sensor", "note": "Current/power monitor"},
        {"part": "INA226", "kind": "Current sensor", "note": "Current/power monitor"},
        {
            "part": "PCA9685",
            "kind": "PWM/servo driver",
            "note": "16-channel PWM controller",
        },
        {
            "part": "Si7021",
            "kind": "Humidity sensor",
            "note": "Humidity/temperature sensor",
        },
    ],
    0x42: [
        {"part": "INA219", "kind": "Current sensor", "note": "Current/power monitor"},
        {"part": "INA226", "kind": "Current sensor", "note": "Current/power monitor"},
        {
            "part": "PCA9685",
            "kind": "PWM/servo driver",
            "note": "16-channel PWM controller",
        },
        {
            "part": "Si7021",
            "kind": "Humidity sensor",
            "note": "Humidity/temperature sensor",
        },
    ],
    0x43: [
        {"part": "INA219", "kind": "Current sensor", "note": "Current/power monitor"},
        {"part": "INA226", "kind": "Current sensor", "note": "Current/power monitor"},
        {
            "part": "PCA9685",
            "kind": "PWM/servo driver",
            "note": "16-channel PWM controller",
        },
        {
            "part": "Si7021",
            "kind": "Humidity sensor",
            "note": "Humidity/temperature sensor",
        },
    ],
    0x44: [
        {"part": "INA219", "kind": "Current sensor", "note": "Current/power monitor"},
        {"part": "INA226", "kind": "Current sensor", "note": "Current/power monitor"},
        {
            "part": "PCA9685",
            "kind": "PWM/servo driver",
            "note": "16-channel PWM controller",
        },
        {
            "part": "Si7021",
            "kind": "Humidity sensor",
            "note": "Humidity/temperature sensor",
        },
    ],
    0x45: [
        {"part": "INA219", "kind": "Current sensor", "note": "Current/power monitor"},
        {"part": "INA226", "kind": "Current sensor", "note": "Current/power monitor"},
        {
            "part": "PCA9685",
            "kind": "PWM/servo driver",
            "note": "16-channel PWM controller",
        },
        {
            "part": "Si7021",
            "kind": "Humidity sensor",
            "note": "Humidity/temperature sensor",
        },
    ],
    0x46: [
        {"part": "INA219", "kind": "Current sensor", "note": "Current/power monitor"},
        {"part": "INA226", "kind": "Current sensor", "note": "Current/power monitor"},
        {
            "part": "PCA9685",
            "kind": "PWM/servo driver",
            "note": "16-channel PWM controller",
        },
        {
            "part": "Si7021",
            "kind": "Humidity sensor",
            "note": "Humidity/temperature sensor",
        },
    ],
    0x47: [
        {"part": "INA219", "kind": "Current sensor", "note": "Current/power monitor"},
        {"part": "INA226", "kind": "Current sensor", "note": "Current/power monitor"},
        {
            "part": "PCA9685",
            "kind": "PWM/servo driver",
            "note": "16-channel PWM controller",
        },
        {
            "part": "Si7021",
            "kind": "Humidity sensor",
            "note": "Humidity/temperature sensor",
        },
    ],
    0x50: [
        {"part": "24C01", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C02", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C04", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C08", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C16", "kind": "EEPROM", "note": "I²C EEPROM"},
    ],
    0x51: [
        {"part": "24C01", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C02", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C04", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C08", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C16", "kind": "EEPROM", "note": "I²C EEPROM"},
    ],
    0x52: [
        {"part": "24C01", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C02", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C04", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C08", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C16", "kind": "EEPROM", "note": "I²C EEPROM"},
    ],
    0x53: [
        {"part": "24C01", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C02", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C04", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C08", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C16", "kind": "EEPROM", "note": "I²C EEPROM"},
    ],
    0x54: [
        {"part": "24C01", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C02", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C04", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C08", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C16", "kind": "EEPROM", "note": "I²C EEPROM"},
    ],
    0x55: [
        {"part": "24C01", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C02", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C04", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C08", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C16", "kind": "EEPROM", "note": "I²C EEPROM"},
    ],
    0x56: [
        {"part": "24C01", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C02", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C04", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C08", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C16", "kind": "EEPROM", "note": "I²C EEPROM"},
    ],
    0x57: [
        {"part": "24C01", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C02", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C04", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C08", "kind": "EEPROM", "note": "I²C EEPROM"},
        {"part": "24C16", "kind": "EEPROM", "note": "I²C EEPROM"},
    ],
    0x12: [
        {
            "part": "PMSA003I",
            "kind": "Particulate sensor",
            "note": "Particulate matter sensor",
        }
    ],
}


def lookup(addr: int) -> list[dict[str, str]]:
    """
    Look up I²C address and return list of candidate parts.

    Args:
        addr: 7-bit I²C address

    Returns:
        List of candidate part dictionaries, or empty list for unknown addresses
    """
    return _ADDRESS_BOOK.get(addr, [])


# Test that the book is data-shaped (dict/JSON, no branching logic)
def get_address_book() -> dict[int, list[dict[str, str]]]:
    """Return the full address book as data structure for data-shape testing"""
    return _ADDRESS_BOOK
