# Raspberry Pi Zero Master Pinout

This document provides a master pinout for the Raspberry Pi Zero used in this project, detailing all GPIO pins and their current assignments.

## Pinout Table

| **Pin Number** | **BCM Pin** | **Function**                  | **Description**                          |
|----------------|-------------|-------------------------------|------------------------------------------|
| 1              | 3.3V        | Power                        | 3.3V Power Supply                        |
| 2              | 5V          | Power                        | 5V Power Supply                          |
| 3              | GPIO 2 (SDA)| I2C Data                     | Connected to ADS1115 and TCS34725        |
| 4              | 5V          | Power                        | 5V Power Supply                          |
| 5              | GPIO 3 (SCL)| I2C Clock                    | Connected to ADS1115 and TCS34725        |
| 6              | GND         | Ground                       | Common Ground                            |
| 7              | GPIO 4      | DHT22 Data                   | Temperature and Humidity Sensor          |
| 8              | GPIO 14 (TX)| UART TX                      | Unused                                   |
| 9              | GND         | Ground                       | Common Ground                            |
| 10             | GPIO 15 (RX)| UART RX                      | Unused                                   |
| 11             | GPIO 17     | LED Control                  | Status LED                               |
| 12             | GPIO 18     | Unused                       | Available                                |
| 13             | GPIO 27     | I2C SDA (TCS34725)           | Color Sensor                             |
| 14             | GND         | Ground                       | Common Ground                            |
| 15             | GPIO 22     | I2C SCL (TCS34725)           | Color Sensor                             |
| 16             | GPIO 23     | Unused                       | Available                                |
| 17             | 3.3V        | Power                        | 3.3V Power Supply                        |
| 18             | GPIO 24     | Unused                       | Available                                |
| 19             | GPIO 10 (MOSI)| Unused                     | Available                                |
| 20             | GND         | Ground                       | Common Ground                            |
| 21             | GPIO 9 (MISO)| Unused                      | Available                                |
| 22             | GPIO 25     | Flow Sensor                  | Measures water flow                      |
| 23             | GPIO 11 (SCLK)| Unused                     | Available                                |
| 24             | GPIO 8 (CE0)| Unused                       | Available                                |
| 25             | GND         | Ground                       | Common Ground                            |
| 26             | GPIO 7 (CE1)| Unused                       | Available                                |
| 27             | ID_SD       | I2C ID EEPROM                | Unused                                   |
| 28             | ID_SC       | I2C ID EEPROM                | Unused                                   |
| 29             | GPIO 5      | Unused                       | Available                                |
| 30             | GND         | Ground                       | Common Ground                            |
| 31             | GPIO 6      | Unused                       | Available                                |
| 32             | GPIO 12     | Unused                       | Available                                |
| 33             | GPIO 13     | Wind Sensor                  | Measures wind speed                      |
| 34             | GND         | Ground                       | Common Ground                            |
| 35             | GPIO 19     | Unused                       | Available                                |
| 36             | GPIO 16     | Unused                       | Available                                |
| 37             | GPIO 26     | Unused                       | Available                                |
| 38             | GPIO 20     | Unused                       | Available                                |
| 39             | GND         | Ground                       | Common Ground                            |
| 40             | GPIO 21     | Unused                       | Available                                |

## Notes
- **ADS1115 (I2C):** Uses GPIO 2 (SDA, Pin 3) and GPIO 3 (SCL, Pin 5) for communication.
- **TCS34725 (I2C Color Sensor):** Shares the same I2C bus as the ADS1115.
- **DHT22:** Connected to GPIO 4 (Pin 7) for temperature and humidity readings.
- **Flow Sensor:** Connected to GPIO 25 (Pin 22) for pulse counting.
- **Wind Sensor:** Connected to GPIO 13 (Pin 33) for pulse counting.
- **LED:** Controlled via GPIO 17 (Pin 11) for status indication.

This pinout ensures no conflicts between devices and provides a clear overview of available pins for future expansion.
