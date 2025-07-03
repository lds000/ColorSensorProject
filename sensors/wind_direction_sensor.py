import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime

# Calibration constants (adjust as needed)
CAL_N_RAW = 14350  # North
CAL_E_RAW = 21755  # East
COMPASS_LABELS = [
    "N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"
]

def raw_to_degrees(raw):
    """
    Map raw ADC value to degrees using calibration points.
    14350 (N) -> 0°, 21755 (E) -> 90°, wraps for other directions.
    """
    if raw < CAL_N_RAW:
        deg = 270 + (raw / (CAL_N_RAW - 655)) * 90
        if deg > 360:
            deg -= 360
        return deg
    elif raw <= CAL_E_RAW:
        deg = (raw - CAL_N_RAW) * 90 / (CAL_E_RAW - CAL_N_RAW)
        return max(0, deg)
    else:
        deg = 90 + (raw - CAL_E_RAW) * 270 / (32767 - CAL_E_RAW)
        if deg > 360:
            deg -= 360
        return deg

def degrees_to_compass(degrees):
    idx = int((degrees + 22.5) // 45)
    return COMPASS_LABELS[idx]

class WindDirectionSensor:
    """Encapsulates wind direction sensor logic using ADS1115 ADC."""
    def __init__(self, ads, channel=ADS.P1):
        self.ads = ads
        self.channel = channel
        self.chan = AnalogIn(self.ads, self.channel)

    def read(self):
        try:
            raw = self.chan.value
            deg = raw_to_degrees(raw)
            compass = degrees_to_compass(deg)
            return {
                "timestamp": datetime.now().isoformat(),
                "wind_direction_raw": raw,
                "wind_direction_deg": deg,
                "wind_direction_compass": compass
            }
        except Exception:
            return {
                "timestamp": datetime.now().isoformat(),
                "wind_direction_raw": None,
                "wind_direction_deg": None,
                "wind_direction_compass": None
            }
