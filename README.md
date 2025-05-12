# Pinecil Settings Manager

A small command-line utility to interact with Pine64 Pinecil v2 soldering irons via the `pinecil` Python library.  
Supports dumping and restoring device settings, inspecting current state, and pretty-printing saved configurations.

---

## Features

- **save**: Fetch current settings and firmware version, pretty-print them, and save as a `(version, settings)` JSON file.  
- **write**: Load a settings JSON, warn if firmware versions differ, diff against device, apply only changed settings, and commit to flash.  
- **info**: Pretty-print live device state (settings, device info, and live telemetry).  
- **graph**: Get a live graph inside the terminal of the tip and handle temperatures, as well as power draw. 
- **print**: Inspect a saved JSON settings file, showing its firmware version and stored settings.

---

## Installation

Install the `pinecil` library:  
```bash
pip install pinecil
```

For graph support, install the `asciichartpy` and `shutil` library:
```bash
pip install asciichartpy shutil
```
Ensure you have Python 3.7+ and asyncio support.

## Usage

```
python pinecil_settings_manager.py <command> [arguments]
```
## Commands
### save

Dump the current device settings to a pickle, annotated with firmware version.
```
python pinecil_settings_manager.py save filename # Creates `mysettings_v1.0.3.json`, pretty-prints settings being saved.

# filename: Base name (without extension). The script appends _v<version>.json.
```
### write

Load a settings pickle and apply only changed values to the device.
```
python pinecil_settings_manager.py write path/to/mysettings_v1.0.3.json
```
- Prompts `[y/N]` if the firmware version in the file differs from the device’s.

- Shows a diff of changed settings before applying.

- Calls save_to_flash() once after the updates.

### info

Fetch and pretty-print the device’s current state:
```
python pinecil_settings_manager.py info
```
- SETTINGS: All saved settings.

- INFO: Device metadata (e.g. firmware version, serial number).

- LIVE DATA: Real-time telemetry (e.g. actual tip temperature, PWM).

### graph

Get a live graph inside the terminal of the tip and handle temperatures, as well as power draw, using the wonderful `asciichartpy` library:
```
python pinecil_settings_manager.py graph
```

### print

Inspect a saved pickle file without connecting to a device:
```
python pinecil_settings_manager.py print path/to/settings_file.json
```
Shows the stored firmware version and all settings in a human-readable table.

## Examples

1. Save settings to disk
```
python pinecil_settings_manager.py save settings_backup
```
2. Inspect the backup
```
python pinecil_settings_manager.py print settings_backup_v1.0.3.json
```
3. Restore to device
```
python pinecil_settings_manager.py write settings_backup_v1.0.3.json
```
4. Check live device data
```
python pinecil_settings_manager.py info
```
5. Get a live graph of the tip and handle temperatures, as well as power draw.
```
python pinecil_settings_manager.py graph
```
## Troubleshooting

### No devices found:
Ensure your Pinecil is powered on and has bluetooth enabled (in advanced settings). Only firmware versions 2.21 and above have bluetooth support. See [here](https://wiki.pine64.org/wiki/Pinecil_Firmware#Bluetooth+(BLE)+Apps)

### Version mismatch warning:
If firmware changed since you saved settings, confirm before writing. Settings names or values may have shifted.
