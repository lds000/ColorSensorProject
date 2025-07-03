import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime

class PressureSensor:
    """Encapsulates pressure sensor logic using ADS1115 ADC."""
    def __init__(self, ads, channel=ADS.P0):
        self.ads = ads
        self.channel = channel
        self.chan = AnalogIn(self.ads, self.channel)

    def read(self):
        try:
            voltage = self.chan.voltage
            if voltage is not None:
                psi = (voltage - 0.5) * (100 / (4.5 - 0.5))
                psi = max(0, min(psi, 100))
                kpa = psi * 6.89476
                return {
                    "timestamp": datetime.now().isoformat(),
                    "pressure_psi": psi,
                    "pressure_kpa": kpa
                }
            else:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "pressure_psi": None,
                    "pressure_kpa": None
                }
        except Exception:
            return {
                "timestamp": datetime.now().isoformat(),
                "pressure_psi": None,
                "pressure_kpa": None
            }
