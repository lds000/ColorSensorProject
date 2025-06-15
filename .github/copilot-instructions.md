# GitHub Copilot Instructions for Sprinkler Controller Project

## Project Context
- This repository is a Raspberry Pi-based sprinkler controller system.
- It uses Python, systemd services, GPIO, MQTT (Mosquitto), and Flask for API endpoints.
- Robust error handling, logging, and system status reporting are critical.
- The project is deployed on real hardware and interacts with sensors and relays.

## Coding Guidelines
- Use clear, descriptive variable and function names.
- Prefer explicit error handling and always log critical errors to `error_log.txt`.
- When suggesting code for GPIO or hardware access, always check for resource conflicts and handle exceptions robustly.
- For MQTT, use the `paho-mqtt` library and publish status updates to `status/watering` every 2 seconds.
- Scripts should be executable and easy to run from the command line.
- Avoid removing or rewriting large blocks of existing logic unless explicitly requested.
- When adding new features, preserve all original functionality unless told otherwise.

## Documentation & Comments
- Add comments explaining hardware interactions, error handling, and any systemd or process management logic.
- Include docstrings for all new functions and classes.

## Security & Safety
- Never suggest code that could damage hardware (e.g., setting all GPIO pins high simultaneously).
- Do not suggest code that disables safety checks or error logging.
- Do not suggest code that grants Copilot or any AI assistant direct access to the terminal or system shell.

## Testing & Debugging
- When suggesting test scripts, prefer minimal, isolated tests (e.g., `test_gpio.py`) for hardware troubleshooting.
- Suggest logging extra debug info (e.g., process lists, lsof output) when diagnosing persistent errors.

## Miscellaneous
- If unsure about a user request, ask for clarification before making large changes.
- Always preserve user data and configuration files.

## System Purpose and Overview

This project is a robust, production-grade Raspberry Pi-based sprinkler controller system. It is designed to automate and monitor garden/yard watering using a combination of:
- **Python** for all core logic and scripts
- **GPIO** for relay and sensor control (relays, flow meter, wind sensor, etc.)
- **MQTT (Mosquitto)** for real-time status and remote sensor integration
- **Flask** for HTTP API endpoints (local and remote access)
- **systemd** for reliable service management and auto-restart
- **Logging** for all errors and system events to `error_log.txt` and other log files

The system is intended for real hardware deployment and interacts with relays, sensors (flow, pressure, wind, soil moisture), and remote devices (e.g., Pi Zero for remote sensing).

---

## Main Components and Structure

- `main.py`: Main controller script. Handles schedule, manual runs, misting logic, GPIO setup, MQTT status publishing, and background threads.
- `flask_api.py`: Flask HTTP API for status, manual control, and data endpoints.
- `gpio_controller.py`: GPIO setup, relay/LED control, and status LED logic.
- `run_manager.py`: Core logic for running watering sets, pulse/soak cycles, and logging history.
- `scheduler.py`: Schedule file loading and watering day logic.
- `status.py`: Global state for current run.
- `logger.py`: Logging utility for status and error logs.
- `config.py`: Pin assignments for relays and other hardware.
- `test_gpio.py`, `windtest.py`: Minimal test scripts for hardware troubleshooting.
- `check.py`: System status and error log checker.
- `sprinkler.service`: systemd unit file for running `main.py` as a service.

---

## MQTT Endpoints and Usage

- **Broker:** Typically Mosquitto, running on the controller Pi (default port 1883)
- **Status Publishing:**
  - Topic: `status/watering`
  - Interval: Every 2 seconds
  - Payload: JSON with timestamp, mist state, last completed run, GPIO status, etc.
- **Remote Sensor Integration:**
  - Remote Pis (e.g., Pi Zero) publish sensor data to MQTT topics (configurable in their scripts)
  - Main controller subscribes or fetches as needed
- **Test/Debug:**
  - Use `mosquitto_sub -h <broker_ip> -t "#" -v` to monitor all MQTT traffic

---

## Flask API Endpoints (see `flask_api.py` for details)
- `/status`: Returns current system status, run info, mist state, etc.
- `/env-data`, `/sets-data`, `/plant-data`, `/environment-data`: Accept POSTs with environmental readings
- `/env-history`, `/env-latest`, `/sets-latest`, `/plant-latest`, `/environment-latest`: Provide historical/latest sensor data
- `/stop-all`: POST endpoint to stop all watering
- `/set-test-mode`: POST endpoint to enable/disable test mode
- `/mist-status`: Returns current misting state
- `/history`, `/history-log`: Returns watering history
- `/soil-latest`: Returns latest soil reading

---

## Data & Log Files
- `sprinkler_schedule.json`: Watering schedule
- `manual_command.json`: Manual run commands
- `watering_history.log`/`watering_history.jsonl`: Watering event logs
- `env_readings.log`, `soil_readings.log`: Environmental and soil sensor logs
- `mist_status.json`, `last_completed_run.json`: State files for API/status
- `error_log.txt`: All critical errors and debug info

---

## Safety, Error Handling, and Debugging
- All GPIO access is protected with error handling and resource conflict checks
- All critical errors are logged to `error_log.txt` (with extra debug info like `lsof` and `ps aux` output for GPIO errors)
- Systemd ensures only one instance of the controller runs at a time
- Test scripts (`test_gpio.py`, `windtest.py`) are provided for isolated hardware troubleshooting
- System status can be checked with `check.py` or `check_sprinkler_service_status.sh`

---

## Extending and Integrating
- New sensors can be added by updating `config.py` and extending the relevant fetch/post logic
- Remote Pis can be integrated via MQTT or HTTP endpoints
- All new features should preserve existing logic and robust error handling

---

## Quick Reference: How to Monitor and Control
- **Start/stop service:** `sudo systemctl start|stop sprinkler`
- **Check status:** `sudo systemctl status sprinkler` or run `./check`
- **Monitor MQTT:** `mosquitto_sub -h <broker_ip> -t "#" -v`
- **Test GPIO:** `python3 test_gpio.py`
- **Test wind sensor:** `python3 windtest.py`

---

## Contact & Support
- For hardware wiring, sensor integration, or advanced troubleshooting, see project documentation or contact the maintainer.

---
These instructions are intended to help Copilot and other AI tools provide safe, robust, and context-aware suggestions for this project.

# Copilot Custom Instructions for Sensor Pi (Color Sensor Project)

**Purpose:**
This project implements a comprehensive environmental and irrigation monitoring system using a Raspberry Pi Zero W (Sensor Pi) and a Raspberry Pi 4 Model B (Sprinkler Main Module). The system collects and reports real-time data from multiple sensors for remote monitoring, automation, and logging via MQTT. A WPF client application is used for monitoring, scheduling, and control.

**Network Topology & Device Roles:**
- **100.111.141.110** (Developer/Client Machine):
  - Runs the WPF application for monitoring and controlling the system.
  - Connects to the MQTT broker and Raspberry Pi devices for schedule uploads, control, and data monitoring.
- **100.117.254.20** (Raspberry Pi Zero W, Sensor Pi):
  - Collects sensor data (environment, plant, soil) and publishes to the MQTT broker.
- **100.116.147.6** (Raspberry Pi 4 Model B, Sprinkler Main Module):
  - Main controller for the sprinkler system, receives commands and schedules, controls watering hardware, and typically runs the MQTT broker (Mosquitto).

**Usage Guidance:**
- Use the above IP addresses according to their described roles in code and configuration.
- The WPF application connects to the Pi 4 for schedule uploads and control, and subscribes to MQTT topics for sensor data from the Pi Zero W.
- Update broker addresses or endpoints in the relevant service or configuration files if network changes are made.

**Hardware Platform:**
- Raspberry Pi Zero W (headless, managed via SSH and systemd)
- Raspberry Pi 4 Model B (main controller, MQTT broker)
- 5V/3.3V logic (all sensors compatible with Pi Zero W voltage levels)

**Sensor Integration (Sensor Pi):**
- **Flow Sensor:**
  - Model: YF-S201 (or similar)
  - Output: Open-drain pulse (Hall effect)
  - GPIO: BCM 25 (physical pin 22)
  - Pull-up: Internal (GPIO.PUD_UP)
  - Calibration: 450 pulses/litre
- **Wind Speed Sensor (Anemometer):**
  - Model: Switch-based anemometer (reed switch)
  - Output: Open/close pulse
  - GPIO: BCM 13 (physical pin 33)
  - Pull-up: External 10kΩ to 3.3V (required)
  - Calibration: 20 pulses = 1 rotation = 1.75 m/s
  - Note: No GPIO interrupts, polling only
- **Color/Moisture Sensor:**
  - Model: TCS34725 (I2C color sensor)
  - I2C SCL: GPIO 22 (physical pin 3)
  - I2C SDA: GPIO 27 (physical pin 13)
  - Address: 0x29 (default)
  - Used for: Plant color, moisture proxy, and lux
- **Temperature/Humidity Sensor:**
  - Model: DHT22 (AM2302)
  - Data: GPIO 4 (physical pin 7)
  - Power: 3.3V or 5V (check sensor)
  - Pull-up: 10kΩ between data and VCC (external recommended)
- **Pressure Sensor:**
  - (Optional, not always present)
  - Requires ADC (e.g., MCP3008) for analog input
  - Not currently implemented in main code

**Wiring Table:**
| Sensor         | Model      | Pi GPIO (BCM) | Physical Pin | Notes                        |
| --------------| ---------- | ------------- | ------------ | ---------------------------- |
| Flow          | YF-S201    | 25            | 22           | Internal pull-up             |
| Wind          | Anemometer | 13            | 33           | External 10kΩ pull-up        |
| Color         | TCS34725   | 22 (SCL)      | 3            | I2C                          |
| Color         | TCS34725   | 27 (SDA)      | 13           | I2C                          |
| Temp/Humidity | DHT22      | 4             | 7            | External 10kΩ pull-up        |

**Software/Code Structure:**
- Main program: `SensorMonitor.py` (Sensor Pi)
  - Polls all sensors in a loop (no interrupts)
  - Robust error handling and debug output
  - Designed for systemd service and remote SSH management
- Main controller: `main.py` (Sprinkler Main Module)
  - Handles schedule, manual runs, misting logic, GPIO setup, MQTT status publishing, and background threads
  - Flask API for status, manual control, and data endpoints
  - Logging to `error_log.txt` and other log files
- WPF Client: For schedule management, manual control, and system status visualization

**MQTT Reporting:**
- **Broker IP:** 100.116.147.6 (typically on Pi 4)
- **Broker Port:** 1883
- **Client:** paho-mqtt (Python)
- **Topics and Data:**
  - `sensors/sets` (flow, pressure)
    - **Frequency:** Every 1 second
    - **Payload Example:**
      ```json
      {
        "timestamp": "2025-06-15T12:00:00.000000",
        "flow_pulses": 12,
        "flow_litres": 0.026,
        "pressure_kpa": null
      }
      ```
  - `sensors/environment` (temperature, humidity, wind speed, barometric pressure)
    - **Frequency:** Every 1 second (if DHT22 returns valid data)
    - **Payload Example:**
      ```json
      {
        "timestamp": "2025-06-15T12:00:00.000000",
        "temperature": 23.5,
        "humidity": 45.2,
        "wind_speed": 2.1,
        "barometric_pressure": null
      }
      ```
  - `sensors/plant` (color, lux, moisture, soil temp)
    - **Frequency:** Every 5 minutes (average of 4 readings, spaced 2 seconds apart)
    - **Payload Example:**
      ```json
      {
        "timestamp": "2025-06-15T12:00:00.000000",
        "moisture": 120,
        "lux": 350.5,
        "soil_temperature": null
      }
      ```
  - `status/watering` (Sprinkler Main Module)
    - **Frequency:** Every 2 seconds
    - **Payload:** JSON with timestamp, mist state, last completed run, GPIO status, etc.

**Best Practices:**
- Always use BCM numbering for GPIO in code and wiring
- Use external pull-up resistors for mechanical sensors (wind, DHT22)
- Confirm I2C devices with `i2cdetect -y 1` before running code
- Use systemd for autostart and reliability
- All sensor data is published via MQTT for remote monitoring
- Log all critical errors to `error_log.txt`
- Test scripts (`test_gpio.py`, `windtest.py`) are provided for hardware troubleshooting

**Security & Safety:**
- Never suggest code that could damage hardware (e.g., setting all GPIO pins high simultaneously)
- Do not suggest code that disables safety checks or error logging
- Do not suggest code that grants Copilot or any AI assistant direct access to the terminal or system shell

**Testing & Debugging:**
- Prefer minimal, isolated test scripts for hardware troubleshooting
- Suggest logging extra debug info (e.g., process lists, lsof output) when diagnosing persistent errors

**Extending and Integrating:**
- New sensors can be added by updating config and extending the relevant fetch/post logic
- Remote Pis can be integrated via MQTT or HTTP endpoints
- All new features should preserve existing logic and robust error handling

## Pi Zero (Sensor Pi) - Integration, Security, and Best Practices

### 1. Custom Authentication or Security Requirements
- **MQTT:**
  - By default, publishes to broker at 100.116.147.6:1883 with no authentication (anonymous access).
  - To enable authentication, configure Mosquitto on the broker Pi to require username/password, and update the Pi Zero’s code:
    ```python
    mqtt_client.username_pw_set("lds00", "Celica1!")
    ```
  - No TLS/SSL by default, but can be added for secure deployments.
- **SFTP:**
  - Not used by default for sensor data. If needed, use SSH key-based authentication.
- **API:**
  - Pi Zero does not expose an HTTP API by default; only publishes to MQTT.

### 2. Additional MQTT Topics or Message Formats
- **Default topics:**
  - sensors/sets (flow, pressure)
  - sensors/environment (temperature, humidity, wind speed, barometric pressure)
  - sensors/plant (color, lux, moisture, soil temp)
- **Message format:**
  - All payloads are JSON, with a timestamp and relevant sensor fields.
- **Custom topics:**
  - You can add more topics (e.g., sensors/soil, sensors/errors) by extending the code.
- **Retained messages:**
  - By default, messages are not retained. Add `retain=True` to `mqtt_client.publish()` if you want the broker to store the last value.

### 3. Special Startup/Shutdown, Failover, or Recovery Logic
- **Startup:**
  - Main script is designed to run as a systemd service for auto-restart and reliability.
  - If the script crashes, systemd will restart it.
- **Shutdown:**
  - On shutdown, the script should clean up GPIO (using `GPIO.cleanup()`).
- **Failover:**
  - No built-in MQTT broker failover. If the broker is unreachable, the script will log errors and retry.
- **Recovery:**
  - If a sensor read fails, the script logs the error and continues polling.

### 4. Hardware Quirks, Limitations, or Required Workarounds
- **GPIO:**
  - Only one process can access a GPIO pin at a time.
  - Use external pull-up resistors for mechanical sensors (wind, DHT22).
- **Voltage:**
  - All sensor signals must be 3.3V logic for Pi Zero compatibility.
  - If using 5V sensors, use a voltage divider or logic level shifter.
- **I2C:**
  - Confirm I2C devices are detected with `i2cdetect -y 1` before running code.
- **Wind sensor:**
  - Some anemometers require polling, not interrupts.
- **Systemd:**
  - Use systemd for reliable autostart and recovery.

### 5. Integration with Cloud Services or External APIs
- **Default:**
  - Pi Zero does not integrate with any cloud services out of the box.
- **Extending:**
  - You can add code to forward MQTT data to cloud platforms (e.g., AWS IoT, Azure IoT, Adafruit IO) or to call external APIs as needed.

### 6. User Roles, Permissions, or Multi-User Logic in the WPF Client
- **WPF Client:**
  - No user roles or permissions are enforced by the Pi Zero or its MQTT topics.
  - Any client with network access and MQTT credentials (if enabled) can subscribe to sensor data.
  - If you need role-based access, implement it in the WPF client or broker configuration.

---

## Sprinkler Controller (Pi 4) - System Summary

Purpose & Role:
---------------
- The Pi 4 acts as the main controller for the smart sprinkler system.
- It manages watering schedules, manual runs, misting logic, and controls relays for valves/pumps.
- Aggregates system status and publishes updates for remote monitoring.

Hardware Details:
-----------------
- **GPIO Usage:**
  - Controls relays for sprinkler valves and misting (see `config.py` for pin assignments)
  - May monitor local sensors (e.g., flow, pressure, wind, soil moisture) if connected
  - Status LED(s) for system state indication
- **Wiring/Safety:**
  - Relays must be 3.3V/5V logic compatible and properly isolated
  - Never set all GPIO outputs high simultaneously (hardware safety)
  - Use opto-isolated relay boards for valve control

Software Architecture:
----------------------
- **Main script:** `main.py` (core logic: schedule, manual runs, misting, MQTT, background threads)
- **API:** `flask_api.py` (Flask HTTP API for status, manual control, data endpoints)
- **GPIO:** `gpio_controller.py` (GPIO setup, relay/LED control)
- **Run logic:** `run_manager.py` (watering sets, pulse/soak cycles, history)
- **Scheduler:** `scheduler.py` (schedule file loading, watering day logic)
- **Status:** `status.py` (global state)
- **Logging:** `logger.py` (status and error logs)
- **Config:** `config.py` (pin assignments)
- **Systemd service:**
  - Configured to auto-start `main.py` and restart on failure
  - Ensures only one instance runs at a time

MQTT Usage:
-----------
- **Publishes to topic:**
  - `status/watering` (system status, run info, GPIO state) every 2 seconds
- **Subscribes to topics:**
  - (Optional) Remote sensor data (e.g., from Pi Zero)
- **Message format:** JSON, e.g.:
  {
    "timestamp": "2025-06-15T12:00:00.000000",
    "mist_state": false,
    "last_completed_run": "2025-06-15T08:00:00.000000",
    "gpio_status": {"valve1": false, "valve2": true}
  }

API Endpoints:
--------------
- **Flask API:**
  - `/status`, `/env-data`, `/sets-data`, `/plant-data`, `/environment-data`, `/env-history`, `/env-latest`, `/sets-latest`, `/plant-latest`, `/environment-latest`, `/stop-all`, `/set-test-mode`, `/mist-status`, `/history`, `/history-log`, `/soil-latest`
  - See `flask_api.py` for details and request/response formats

Error Handling:
---------------
- All critical errors logged to `error_log.txt` (with extra debug info for GPIO/MQTT errors)
- Systemd restarts service on failure
- System status can be checked with `check.py` or `systemctl status sprinkler`

Security:
---------
- **MQTT:** No authentication/TLS by default (can be enabled in broker and client config)
- **API:** No authentication by default; can be added to Flask endpoints if needed
- **Systemd:** Ensures only one instance runs; prevents resource conflicts

Extensibility:
--------------
- To add new relays/sensors: update `config.py` and extend relevant modules
- To add new API endpoints: update `flask_api.py`
- To integrate remote Pis: subscribe to their MQTT topics or add HTTP fetch logic

---

## WPF Client (C#) - System Summary

Purpose & Role:
---------------
- The WPF client is a desktop application for monitoring, scheduling, and manual control of the sprinkler system.
- Provides a live dashboard, schedule editor, manual run controls, and history viewer.

Network Interaction:
--------------------
- **MQTT:**
  - Subscribes to: `sensors/environment`, `sensors/plant`, `sensors/sets`, `status/watering`
  - Receives real-time sensor and system status updates
- **SFTP/SSH:**
  - Used for uploading `sprinkler_schedule.json` and `manual_command.json` to the Pi 4
- **IP Addresses:**
  - Connects to Pi 4 (default: 100.116.147.6) and Pi Zero (default: 100.117.254.20) as configured

MQTT Topics:
------------
- **Subscribed topics:**
  - `sensors/environment`, `sensors/plant`, `sensors/sets`, `status/watering`
- **Message format:** JSON, matching the payloads published by the Pis

User Interface:
---------------
- Live sensor dashboard
- Manual control (run once)
- Schedule editor
- History viewer

Error Handling:
---------------
- Connection failures, timeouts, and invalid data are caught and may show a MessageBox or be logged
- Some errors are logged using DebugLogger (not persisted by default)

Security:
---------
- **MQTT:** No authentication/TLS by default (can be enabled in broker and client config)
- **SFTP/SSH:** Password authentication by default; no SSH key management
- **User roles:** Single-user/admin only; no multi-user logic

Extensibility:
--------------
- To add new sensors or topics: update code to subscribe and process new MQTT topics
- To add new UI features: extend the WPF application
- To add authentication: update MQTT/SFTP connection logic

## WPF Client (C#) - MQTT Topic Subscription and Processing Details

MQTT Topics Subscribed by the WPF Client
----------------------------------------

1. **sensors/environment**
   - Message Format: JSON object matching the EnvironmentData model (e.g., temperature, humidity, etc.)
   - Processing: Deserialized into an EnvironmentData object and added to the EnvironmentReadings collection.
   - UI Display: Shown in the live sensor dashboard as real-time environment sensor readings.

2. **sensors/plant**
   - Message Format: JSON object matching the PlantData model (e.g., plant-specific sensor data)
   - Processing: Deserialized into a PlantData object and added to the PlantReadings collection.
   - UI Display: Shown in the live sensor dashboard as plant health or status indicators.

3. **sensors/sets**
   - Message Format: JSON object matching the SetsData model (e.g., set-specific sensor data)
   - Processing: Deserialized into a SetsData object and added to the SetsReadings collection.
   - UI Display: Shown in the live sensor dashboard, often as per-zone or per-set sensor data.

4. **status/watering**
   - Message Format: JSON object matching the PiStatusResponse model, which includes:
     - system_status (string)
     - test_mode (bool)
     - led_colors (dictionary)
     - zones (list of zone statuses)
     - current_run, next_run, last_completed_run (run info objects)
     - upcoming_runs (list)
   - Processing: Deserialized into a PiStatusResponse object. Updates multiple properties:
     - SystemStatus
     - PiReportedTestMode
     - LedColors
     - ZoneStatuses
     - CurrentRun, NextRun, LastCompletedRun
     - UpcomingRuns
   - UI Display: Updates the main dashboard, including system status, test mode, LED indicators, zone statuses, current/next/last run info, and upcoming runs.

General Processing Flow:
------------------------
- All MQTT messages are received as JSON payloads.
- The WPF client deserializes each message according to the topic and updates the corresponding ObservableCollection or property.
- The UI is data-bound to these collections/properties, so updates are reflected in real time (e.g., sensor dashboards, status panels, run history, etc.).

Note:
- The WPF client does not publish to MQTT topics; it is strictly a subscriber for the above topics.

If you need the exact JSON schema for each model, see the WPF client source code or request the schema definitions.

---
