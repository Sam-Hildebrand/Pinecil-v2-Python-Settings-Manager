from pinecil import find_pinecils
import json
import asyncio
import argparse
import itertools
import os
import sys

def pretty_print_dict(title: str, data: dict):
    print(f"\n=== {title} ===")
    if not data:
        print("  (no data)")
        return
    key_width = max(len(str(k)) for k in data.keys())
    for k, v in data.items():
        print(f"  {str(k).ljust(key_width)} : {v}")

async def _spinner(msg: str, done_event: asyncio.Event, delay: float = 0.2):
    frames = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
    for ch in itertools.cycle(frames):
        print(f"\r{msg} {ch}", end='', flush=True)
        if done_event.is_set():
            break
        await asyncio.sleep(delay)
    # clear line
    print('\r' + ' '*(len(msg)+2) + '\r', end='', flush=True)

async def connect_to_iron():
    found = asyncio.Event()
    finding_spin = asyncio.create_task(_spinner("Searching for Pinecil...", found))
    devices = await find_pinecils()
    found.set()
    await finding_spin

    if not devices:
        print("No Pinecil devices found.", file=sys.stderr)
        sys.exit(1)

    connected = asyncio.Event()
    connecting_spin = asyncio.create_task(_spinner("Connecting to Pinecil...", connected))
    iron = devices[0]
    await iron.connect()
    connected.set()
    await connecting_spin

    return iron

async def main(args):

    if args.command == 'save':
        iron = await connect_to_iron()
        
        # Fetch settings and device version
        read_settings = asyncio.Event()
        saving_spin = asyncio.create_task(_spinner("Reading Pinecil Settings...", read_settings))
        settings = await iron.get_all_settings()
        info = await iron.get_info()
        version = info.get('build', 'unknown')
        read_settings.set()
        await saving_spin

        # Show only the settings that will be saved
        print(f"\nSaving settings for firmware version: {version}")
        pretty_print_dict("SETTINGS TO SAVE", settings)

        # Build filename: append version and .json
        base, _ = os.path.splitext(args.filename)
        filename = f"{base}_v{version}.json"

        # Dump a dict with version and settings to JSON
        data = {
            'version': version,
            'settings': settings
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\nSettings saved to JSON file: {filename}")

    elif args.command == 'write':
        iron = await connect_to_iron()

        # Load JSON file
        if not os.path.isfile(args.path):
            print(f"File not found: {args.path}", file=sys.stderr)
            sys.exit(1)
        with open(args.path, 'r') as f:
            data = json.load(f)
        file_version = data.get('version', 'unknown')
        loaded_settings = data.get('settings', {})

        # Fetch current device version
        info = await iron.get_info()
        device_version = info.get('build', 'unknown')

        # Warn if versions differ
        print(f"\nJSON file version      : {file_version}")
        print(f"Device firmware version: {device_version}")
        if file_version != device_version:
            resp = input("Versions differ. Proceed anyway? [y/N]: ").strip().lower()
            if resp != 'y':
                print("Aborted.")
                sys.exit(0)

        # Fetch current settings and diff
        loaded_settings_event = asyncio.Event()
        loading_settings_spin = asyncio.create_task(_spinner("Loading settings...", loaded_settings_event))
        current_settings = await iron.get_all_settings()
        to_update = []
        for name, new_val in loaded_settings.items():
            old_val = current_settings.get(name)
            if old_val != new_val:
                to_update.append((name, old_val, new_val))
        loaded_settings_event.set()
        await loading_settings_spin

        if not to_update:
            print("\nDevice already has all those settings - nothing to do.")
        else:
            print(f"\nUpdating {len(to_update)} setting(s):")
            for name, old_val, new_val in to_update:
                print(f"  {name}: {old_val} --> {new_val}")
                await iron.set_one_setting(name, new_val)
            await iron.save_to_flash()
            print("\nApplied changes and saved to flash.")


    elif args.command == 'info':
        iron = await connect_to_iron()        

        info_gathered = asyncio.Event()
        info_spin = asyncio.create_task(_spinner("Reading data from Pinecil...", info_gathered))
        # Print live device state
        settings = await iron.get_all_settings()
        info = await iron.get_info()
        live = await iron.get_live_data()
        info_gathered.set()
        await info_spin
        pretty_print_dict("SETTINGS", settings)
        pretty_print_dict("INFO", info)
        pretty_print_dict("LIVE DATA", live)

    elif args.command == 'print':
        # Load JSON file
        if not os.path.isfile(args.file):
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, 'r') as f:
            data = json.load(f)
        file_version = data.get('version', 'unknown')
        file_settings = data.get('settings', {})

        # Display header and contents
        print(f"\n=== SETTINGS FILE: {os.path.basename(args.file)} ===")
        print(f"Firmware Version Stored: {file_version}")
        pretty_print_dict("STORED SETTINGS", file_settings)

    elif args.command == 'graph':
        import shutil
        import asciichartpy

        iron = await connect_to_iron()

        temps = []
        handle_temps = []
        powers = []

        try:
            while True:
                live = await iron.get_live_data()
                temp  = live.get('LiveTemp', None)
                handle_temp = live.get('HandleTemp', None)
                power = live.get('Watts', None)

                # Recompute chart height & width from terminal
                size = shutil.get_terminal_size()
                chart_height = max(3, size.lines - 5)         # leave 5 lines for header/margins
                chart_width  = max(10, size.columns - 10)     # leave 10 cols for padding/labels

                if temp is not None and power is not None and handle_temp is not None:
                    handle_temp = handle_temp / 10
                    temps.append(temp)
                    handle_temps.append(handle_temp)
                    powers.append(power)
                    if len(temps) > chart_width:
                        temps.pop(0)
                        handle_temps.pop(0)
                        powers.pop(0)

                    os.system('cls' if os.name == 'nt' else 'clear')
                    # ANSI color codes
                    RED   = '\033[31m'
                    GREEN = '\033[32m'
                    BLUE  = '\033[34m'
                    RESET = '\033[0m'
                    print(
                        f"Pinecil live graph - "
                        f"temp: {RED}{temp:.1f}°C{RESET}, "
                        f"handle temp: {GREEN}{handle_temp:.1f}°C{RESET}, "
                        f"power: {BLUE}{power:.1f} mW{RESET}"
                    )
                    print()
                    chart = asciichartpy.plot(
                        [temps, handle_temps, powers],
                        {
                            'height': chart_height,
                            'width' : chart_width,
                            'colors': [asciichartpy.red, asciichartpy.green, asciichartpy.blue]
                        }
                    )
                    print(chart)
                else:
                    print("Waiting for valid temp & power data…")

                await asyncio.sleep(args.interval)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nExiting graph mode.")

    else:
        parser.print_help()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""
        Get settings and info from an Pine64 Pinecil v2 using the pinecil python library. 
        Can also save settings to a .pkl file and write those settings back to the device.
        Useful when updating firmware, but bare in mind that setting names may change, 
        settings may be removed, and new settings may be added after a firmware update.
        No guarantees given."""
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    save_p = subparsers.add_parser('save', help="Save the devices current settings as a json file")
    save_p.add_argument('filename', help="Base name for output (version & .pkl appended)")

    write_p = subparsers.add_parser('write', help="Write settings from a json file to the device")
    write_p.add_argument('path', help="Path to the .pkl file to load")

    subparsers.add_parser('info', help="Print current settings, info, and live data")

    print_p = subparsers.add_parser('print', help="Print contents of a settings json")
    print_p.add_argument('file', help="Path to the .pkl file to inspect")

    graph_p = subparsers.add_parser('graph', help="Live-plot temperature and power with asciichartpy")
    graph_p.add_argument(
        '--interval', '-i', type=float, default=0.1,
        help="Seconds between samples (default: 0.1)"
    )

    args = parser.parse_args()
    asyncio.run(main(args))
