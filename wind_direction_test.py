import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

"""
wind_direction_test.py

Test script for reading wind direction voltage from ADS1115 channel 1 (A1) on a Raspberry Pi.
- Connect wind vane analog output to A1 (ADS1115 channel 1).
- Prints voltage and raw value every second.
- Designed for troubleshooting and calibration.

Wiring:
- ADS1115 SCL -> Pi SCL (GPIO 3)
- ADS1115 SDA -> Pi SDA (GPIO 2)
- Wind vane analog out -> ADS1115 A1
- ADS1115 VDD -> 3.3V
- ADS1115 GND -> GND

Press Ctrl+C to stop.
"""

# Compass labels for 8 main directions
COMPASS_LABELS = [
    "N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"
]

def voltage_to_degrees(voltage):
    """
    Convert voltage (1-5V) to wind direction in degrees (0-360).
    """
    if voltage < 1.0:
        return 0.0
    if voltage > 5.0:
        voltage = 5.0
    return (voltage - 1.0) * (360.0 / 4.0)

def degrees_to_compass(degrees):
    """
    Convert degrees (0-360) to compass label (N, NE, E, etc.).
    """
    idx = int((degrees + 22.5) // 45)
    return COMPASS_LABELS[idx]

def main():
    print("Wind direction ADC test started. Press Ctrl+C to stop.")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        chan = AnalogIn(ads, ADS.P1)  # Channel 1 (A1)
        while True:
            voltage = chan.voltage
            raw = chan.value
            direction_deg = voltage_to_degrees(voltage)
            compass = degrees_to_compass(direction_deg)
            print(f"A1 voltage: {voltage:.4f} V, raw ADC: {raw}, direction: {direction_deg:.1f}° ({compass})")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
