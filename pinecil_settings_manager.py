from pinecil import find_pinecils  # if running in a cloned repo, use `from src.pinecil`
import pickle
import asyncio
import argparse
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

async def main(args):

    if args.command == 'save':
        # Discover and connect
        devices = await find_pinecils()
        if not devices:
            print("No Pinecil devices found.", file=sys.stderr)
            sys.exit(1)
        iron = devices[0]
        await iron.connect()
        # Fetch settings and device version
        settings = await iron.get_all_settings()
        info = await iron.get_info()
        version = info.get('build', 'unknown')

        # 2) Show only the settings that will be saved
        print(f"\nSaving settings for firmware version: {version}")
        pretty_print_dict("SETTINGS TO SAVE", settings)

        # 3) Build filename: append version and .pkl
        base, _ = os.path.splitext(args.filename)
        filename = f"{base}_v{version}.pkl"

        # 4) Dump a tuple (version, settings)
        with open(filename, 'wb') as f:
            pickle.dump((version, settings), f)
        print(f"\nSettings (with version) saved to pickle file: {filename}")

    elif args.command == 'write':
        # Discover and connect
        devices = await find_pinecils()
        if not devices:
            print("No Pinecil devices found.", file=sys.stderr)
            sys.exit(1)
        iron = devices[0]
        await iron.connect()

        # 1) Load tuple from pickle
        if not os.path.isfile(args.path):
            print(f"File not found: {args.path}", file=sys.stderr)
            sys.exit(1)
        with open(args.path, 'rb') as f:
            file_version, loaded_settings = pickle.load(f)

        # 2) Fetch current device version
        info = await iron.get_info()
        device_version = info.get('build', 'unknown')

        # 3) Warn if versions differ
        print(f"\nPickle file version : {file_version}")
        print(f"Device firmware version: {device_version}")
        if file_version != device_version:
            resp = input("Versions differ. Proceed anyway? [y/N]: ").strip().lower()
            if resp != 'y':
                print("Aborted.")
                sys.exit(0)

        # 4) Fetch current settings and diff
        current_settings = await iron.get_all_settings()
        to_update = []
        for name, new_val in loaded_settings.items():
            old_val = current_settings.get(name)
            if old_val != new_val:
                to_update.append((name, old_val, new_val))

        if not to_update:
            print("\nDevice already has all those settings—nothing to do.")
        else:
            print(f"\nUpdating {len(to_update)} setting(s):")
            for name, old_val, new_val in to_update:
                print(f"  {name}: {old_val} → {new_val}")
                await iron.set_one_setting(name, new_val)
            await iron.save_to_flash()
            print("\nApplied changes and saved to flash.")

    elif args.command == 'info':
        # Discover and connect
        devices = await find_pinecils()
        if not devices:
            print("No Pinecil devices found.", file=sys.stderr)
            sys.exit(1)
        iron = devices[0]
        await iron.connect()

        # Print live device state
        settings = await iron.get_all_settings()
        info = await iron.get_info()
        live = await iron.get_live_data()
        pretty_print_dict("SETTINGS", settings)
        pretty_print_dict("INFO", info)
        pretty_print_dict("LIVE DATA", live)

    elif args.command == 'print':
        # 1) Load tuple from pickle
        if not os.path.isfile(args.file):
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, 'rb') as f:
            file_version, file_settings = pickle.load(f)

        # 2) Display header and contents
        print(f"\n=== SETTINGS FILE: {os.path.basename(args.file)} ===")
        print(f"Firmware Version Stored: {file_version}")
        pretty_print_dict("STORED SETTINGS", file_settings)

    else:
        # Should never happen
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

    save_p = subparsers.add_parser('save', help="Save the devices current settings as a pickle file")
    save_p.add_argument('filename', help="Base name for output (version & .pkl appended)")

    write_p = subparsers.add_parser('write', help="Write settings from a pickle file to the device")
    write_p.add_argument('path', help="Path to the .pkl file to load")

    subparsers.add_parser('info', help="Print current settings, info, and live data")

    print_p = subparsers.add_parser('print', help="Print contents of a settings pickle")
    print_p.add_argument('file', help="Path to the .pkl file to inspect")

    args = parser.parse_args()
    asyncio.run(main(args))
