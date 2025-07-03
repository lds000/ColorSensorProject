import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P0)  # Channel 0

while True:
    voltage = chan.voltage
    # Convert voltage (0.5V = 0 PSI, 4.5V = 100 PSI)
    if voltage is not None:
        psi = (voltage - 0.5) * (100 / (4.5 - 0.5))
        psi = max(0, min(psi, 100))  # Clamp to 0-100 PSI
        print(f"Voltage: {voltage:.3f} V, Pressure: {psi:.2f} PSI")
    else:
        print("Sensor read error")
    time.sleep(1)