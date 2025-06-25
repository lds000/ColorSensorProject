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

# --- Calibration for raw ADC values ---
# User-provided calibration:
#   West-to-East (E): raw = 21755
#   South-to-North (N): raw = 14350
# We'll map 14350 -> 0° (N), 21755 -> 90° (E), and interpolate linearly.
# Full circle assumed to be 0-32767 (ADS1115 default range)

CAL_N_RAW = 14350  # North
CAL_E_RAW = 21755  # East
RAW_MIN = 14350    # Calibrated min (N)
RAW_MAX = 21755    # Calibrated max (E)

# For 8-point compass, we need to extrapolate for S and W as well.
# We'll assume the sensor is linear and wraps around.

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

def raw_to_degrees(raw):
    """
    Map raw ADC value to degrees using calibration points.
    14350 (N) -> 0°, 21755 (E) -> 90°, 29160 (S) -> 180°, 655 (W) -> 270°
    """
    # Calculate scale per degree between N and E
    if raw < CAL_N_RAW:
        # Wrap around for W (raw < N)
        # W is at 270°, so interpolate backwards
        # Assume 0 (or 32767) is W
        # 14350 (N) -> 0°, 655 (W) -> 270°
        # 655 is 270°; 14350 is 0°
        # (14350 - 655) = 13695 raw units for 270°
        deg = 270 + (raw / (CAL_N_RAW - 655)) * 90
        if deg > 360:
            deg -= 360
        return deg
    elif raw <= CAL_E_RAW:
        # N to E
        deg = (raw - CAL_N_RAW) * 90 / (CAL_E_RAW - CAL_N_RAW)
        return max(0, deg)
    else:
        # E to S to W (wrap around)
        # E (21755) -> 90°, S (29160) -> 180°, W (655) -> 270°
        # We'll estimate S as midpoint between E and W
        # 21755 (E) to 32767 (max) is 110°, then wrap to 0
        deg = 90 + (raw - CAL_E_RAW) * 270 / (32767 - CAL_E_RAW)
        if deg > 360:
            deg -= 360
        return deg

def main():
    print("Wind direction ADC test started. Press Ctrl+C to stop.")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        chan = AnalogIn(ads, ADS.P1)  # Channel 1 (A1)
        while True:
            voltage = chan.voltage
            raw = chan.value
            direction_deg = raw_to_degrees(raw)
            compass = degrees_to_compass(direction_deg)
            print(f"A1 voltage: {voltage:.4f} V, raw ADC: {raw}, direction: {direction_deg:.1f}° ({compass})")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
