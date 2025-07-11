"""
Minimal DS18B20 test script for Raspberry Pi
Wiring:
- DS18B20 Data to GPIO4 (physical pin 7)
- VCC to 3.3V or 5V (check sensor spec)
- GND to Pi GND
- 4.7kΩ pull-up resistor between Data and VCC
- Enable 1-Wire: add 'dtoverlay=w1-gpio' to /boot/config.txt and reboot
"""
from w1thermsensor import W1ThermSensor
import time

# Find the connected DS18B20 sensor
def find_ds18b20_sensor():
    for sensor in W1ThermSensor.get_available_sensors():
        if sensor.type == W1ThermSensor.THERM_SENSOR_DS18B20:
            return sensor
    return None

# Read temperature from the sensor
def read_temperature(sensor):
    temperature_celsius = sensor.get_temperature()
    temperature_fahrenheit = sensor.get_temperature(W1ThermSensor.DEGREES_F)
    return temperature_celsius, temperature_fahrenheit

# Find DS18B20 sensor
ds18b20_sensor = find_ds18b20_sensor()

if ds18b20_sensor is not None:
    print(f"DS18B20 Sensor found: {ds18b20_sensor.id}")
    try:
        while True:
            temperature_c, temperature_f = read_temperature(ds18b20_sensor)
            print(f"Temperature: {temperature_c:.2f}°C | {temperature_f:.2f}°F")
            time.sleep(2)
    except KeyboardInterrupt:
        print("Program terminated by user.")
else:
    print("DS18B20 Sensor not found.")
