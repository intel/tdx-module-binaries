#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2025 Chao Gao
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Note: this script may have been developed with support from one or more
# Intel-operated generative artificial intelligence solutions.

import os
import sys
import glob
import json
import argparse
import re
import struct
import time  # Import time module for polling
try:
    import cpuid  # Import cpuid module
except ImportError:
    print("Error: cpuid module is not installed. Please install it using 'pip install cpuid'")
    sys.exit(1)

FIRMWARE_PATH = "/sys/class/firmware/seamldr_upload"
MODULE_PATH = "/sys/devices/faux/tdx_host"
SEAMLDR_PATH = "/sys/devices/faux/tdx_host/seamldr"
allow_debug = False

# Default directory of the module blobs
DEFAULT_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_cpuid_1_eax() -> int:
    """Get the current CPU's CPUID.1.EAX value on Linux.

    Returns:
        int: The EAX register value or None if an error occurs.
    """
    try:
        regs = cpuid.cpuid(0x1)
        return regs[0]  # EAX is the first element in the tuple
    except Exception as e:
        print("Intel TDX module works for Intel CPUs only", e)
        return None

def get_current_module_version() -> str:
    """Read the current module version from sysfs.

    Returns:
        str: The current module version or None if an error occurs.
    """
    try:
        with open(os.path.join(MODULE_PATH, "version"), "r") as f:
            version = f.read().strip()
        return version
    except Exception as e:
        print(f"Error reading current module version: {e}")
        return None

def get_current_seamldr_version() -> str:
    """Read the current seamldr version from sysfs.

    Returns:
        str: The current seamldr version or None if an error occurs.
    """
    try:
        with open(os.path.join(SEAMLDR_PATH, "version"), "r") as f:
            version = f.read().strip()
        return version
    except Exception as e:
        print(f"Error reading current seamldr version: {e}")
        return None

def get_supported_cpu_family_model(blob_path: str) -> list[int]:
    """Determine the supported CPU family models for the module.

    Args:
        blob_path (str): Path to the module blob file.

    Returns:
        list[int]: A list of supported CPU family models.
    """
    supported_CPU_family_model = []

    try:
        with open(blob_path, "rb") as f:
            f.seek(0x1000 + 1024)  # Offset to the sigstruct + offset to the number of entries
            num_entries_bytes = f.read(4)
            if len(num_entries_bytes) != 4:
                raise ValueError("Invalid number of entries length")
            num_entries = struct.unpack("<I", num_entries_bytes)[0]

            f.seek(0x1000 + 1028)  # Offset to the sigstruct + offset to the entries
            for _ in range(num_entries):
                entry_bytes = f.read(4)
                if len(entry_bytes) != 4:
                    raise ValueError("Invalid entry length")
                entry = struct.unpack("<I", entry_bytes)[0]
                family_model = entry & 0xFFFFFFF0  # Ignore the lowest 4 bits (stepping)
                supported_CPU_family_model.append(family_model)
    except Exception as e:
        print(f"Error checking compatibility with current system: {e}")

    return supported_CPU_family_model

def get_module_type(blob_path: str) -> int:
    """Read the module type from the blob file.

    Args:
        blob_path (str): Path to the module blob file.

    Returns:
        int: The module type or None if an error occurs.
    """
    try:
        with open(blob_path, "rb") as f:
            f.seek(0x1000 + 12)
            module_type_bytes = f.read(4)
            # Unpack the bytes into an integer using struct
            module_type = struct.unpack("<I", module_type_bytes)[0]  # "<I" for little-endian unsigned int
            return int(module_type)
    except Exception as e:
        print(f"Error reading module type: {e}")

    return None

class TdxModule:
    def __init__(self, version: str, path: str, CPU_family_model: list[int], module_version: str, seamldr_versions: list[str], tdx_feature0: str, type: int):
        self.version = version
        self.path = path
        self.supported_CPU_family_model = CPU_family_model
        self.min_module_version_for_td_preserving = module_version
        self.min_seamldr_versions = seamldr_versions
        self.tdx_feature0 = tdx_feature0
        self.type = type

def get_all_tdx_modules(directory: str) -> list[TdxModule]:
    """Get all Intel TDX module versions and their metadata in the specified directory.

    Args:
        directory (str): Path to the directory containing Intel TDX modules and mapping file

    Returns:
        list[TdxModule]: A list of TdxModule objects.
    """
    try:
        mapping_file = os.path.join(directory, "mapping_file.json")
        joined_files = os.path.join(directory, "joined_files")

        # Load JSON data
        with open(mapping_file, 'r') as f:
            json_data = json.load(f)

        # Extract relevant information from JSON
        releases_info = {release['version']: release for release in json_data['tdx_module_releases']}

        modules = []
        # Collect directories that match the format "a.b"
        version_dirs = []
        for root, dirs, files in os.walk(joined_files):
            for dir_name in dirs:
                if re.match(r"^\d+\.\d+$", dir_name):
                    version_dirs.append(os.path.join(root, dir_name))

        for version_path in version_dirs:
            blob_files = glob.glob(os.path.join(version_path, "tdx_module_*.blob"))

            for blob_file in blob_files:
                version_match = re.search(r"tdx_module_(\d+\.\d+\.\d+)\.blob", os.path.basename(blob_file))
                if version_match:
                    version = version_match.group(1)
                    # Determine the supported CPU family models
                    supported_CPU_family_model = get_supported_cpu_family_model(blob_file)
                    module_type = get_module_type(blob_file)

                    # Get additional information from JSON
                    release_info = releases_info.get(version)
                    if not release_info:
                        print(f"Skipping module {version}: Missing release information in JSON.")
                        continue

                    min_module_version_for_td_preserving = release_info.get('min_module_version_for_td_preserving')
                    min_seamldr_versions = release_info.get('min_seamldr_versions')
                    tdx_feature0 = release_info.get('tdx_feature0')

                    # Check if any required information is missing
                    if None in (module_type, min_module_version_for_td_preserving, min_seamldr_versions, tdx_feature0):
                        print(f"Skipping module {version}: Missing required information.")
                        continue

                    module = TdxModule(version, blob_file, supported_CPU_family_model, min_module_version_for_td_preserving, min_seamldr_versions, tdx_feature0, module_type)
                    modules.append(module)
        return modules
    except Exception as e:
        print(f"Error reading all modules: {e}")
        return None

def is_compatible_with_seamldr(module: TdxModule, seamldr_version: str) -> bool:
    """Check if the module is compatible with the current seamldr.

    Args:
        module (TdxModule): The Intel TDX module to check compatibility.
        seamldr_version (str): The current seamldr version in x.y.z format.

    Returns:
        bool: True if compatible, False otherwise.
    """
    try:
        # Parse the current seamldr version
        seamldr_major, seamldr_minor, seamldr_update = map(int, seamldr_version.split('.'))

        # Iterate over the minimum required seamldr versions
        for v in module.min_seamldr_versions:
            major, minor, update = map(int, v.split('.'))

            # Check if the major and minor versions match
            if major == seamldr_major and minor == seamldr_minor:
                # Check if the update version is less than or equal to the current update version
                if update <= seamldr_update:
                    return True

    except Exception as e:
        print("Failed to check seamldr compatibility:", e)
        return False

    return False


def is_compatible(module: TdxModule) -> bool:
    """Check if the module is compatible with the current CPU setup.

    Args:
        module (TdxModule): The Intel TDX module to check compatibility.

    Returns:
        bool: True if compatible, False otherwise.
    """
    seamldr_version = get_current_seamldr_version()
    if seamldr_version is None:
        return False

    if not is_compatible_with_seamldr(module, seamldr_version):
        return False

    cpuid_1_eax = get_cpuid_1_eax()
    if cpuid_1_eax is None:
        return False
    cpuid_1_eax_masked = cpuid_1_eax & 0xFFFFFFF0  # Ignore the lowest 4 bits (stepping)
    return cpuid_1_eax_masked in module.supported_CPU_family_model

def is_debug(module: TdxModule) -> bool:
    """Check if the module is a debug module.

    Args:
        module (TdxModule): The Intel TDX module to check.

    Returns:
        bool: True if it is a debug module, False otherwise.
    """
    return module.type & (1 << 31)

def is_td_preserving_capable(module: TdxModule) -> bool:
    """Check if the module is TD preserving capable.

    Args:
        module (TdxModule): The Intel TDX module to check.

    Returns:
        bool: True if TD preserving capable, False otherwise.
    """
    if is_debug(module) and not allow_debug:
        return False

    current_version = get_current_module_version()
    if not current_version:
        return False

    current_major_minor = '.'.join(current_version.split('.')[:2])
    current_update = int(current_version.split('.')[2])

    module_major_minor = '.'.join(module.version.split('.')[:2])
    module_update = int(module.version.split('.')[2])
    min_preserving_update = int(module.min_module_version_for_td_preserving.split('.')[2])

    return module_major_minor == current_major_minor and module_update >= current_update and min_preserving_update <= current_update

def list_tdx_modules(modules: list[TdxModule]) -> None:
    """Print all Intel TDX module versions and their compatibility status.

    Args:
        modules (list[TdxModule]): List of Intel TDX modules to print.
    """
    # Sort modules by version in descending order
    modules.sort(key=lambda m: tuple(map(int, m.version.split('.'))), reverse=True)

    for module in modules:
        debug_status = "[debug]" if is_debug(module) else ""
        td_preserving_capable_status = "[TD-Preserving-incapable]" if not is_td_preserving_capable(module) else ""
        print(f"{module.version} {debug_status}{td_preserving_capable_status}")

def find_newest_tdx_module(modules: list[TdxModule]) -> TdxModule:
    """Find the newest TD-preserving capable Intel TDX module.

    Args:
        modules (list[TdxModule]): List of Intel TDX modules to search.

    Returns:
        TdxModule: The newest TD-preserving capable module, or None if none found.
    """
    # Filter modules that are TD-preserving capable
    td_preserving_modules = [module for module in modules if is_td_preserving_capable(module)]

    # Sort modules by update version in descending order
    td_preserving_modules.sort(key=lambda m: int(m.version.split('.')[2]), reverse=True)

    # Return the module with the highest version
    return td_preserving_modules[0] if td_preserving_modules else None

def update_tdx_module(module: TdxModule) -> None:
    """Update the specified Intel TDX module.

    Args:
        module (TdxModule): The Intel TDX module to update.
    """
    if module is None or module.path is None:
        print("No Intel TDX module found to update.")
        return

    if not is_compatible(module):
        print(f"incompatible module {module.version}")
        return

    if is_debug(module) and not allow_debug:
        print("Cannot load debug module. Try --allow_debug")
        return False

    if not is_td_preserving_capable(module):
        print(f"not td_preserving-capable {module.version}")
        return

    if not os.path.exists(FIRMWARE_PATH):
        print(f"Error: {FIRMWARE_PATH} does not exist.")
        sys.exit(1)

    prev_version = get_current_module_version()
    print(f"Install module {module.path}")

    try:
        # Perform the steps to load the firmware
        with open(f"{FIRMWARE_PATH}/loading", "w") as f:
            f.write("1")
        with open(f"{FIRMWARE_PATH}/data", "wb") as f:
            with open(module.path, "rb") as blob:
                f.write(blob.read())  # Write the entire blob
        with open(f"{FIRMWARE_PATH}/loading", "w") as f:
            f.write("0")

        # Poll the status until it becomes "idle" or timeout after 10 seconds
        timeout = 10
        start_time = time.time()
        while True:
            with open(f"{FIRMWARE_PATH}/status", "r") as f:
                status = f.read().strip()
            if status == "idle":
                break
            if time.time() - start_time > timeout:
                print("Error: Timeout while waiting for status to become 'idle'")
                sys.exit(1)
            time.sleep(1)

        # Bail out if an error occurred
        with open(f"{FIRMWARE_PATH}/error", "r") as f:
            error = f.read().strip()
        if error:
            print(f"Firmware update failed {error}")
            sys.exit(1)

        curr_version = get_current_module_version()
        print(f"Upgrade Intel TDX module from {prev_version} to {curr_version}")

    except Exception as e:
        print(f"Error during installation: {e}")

def main() -> None:
    """Main function to execute the TDX Tool."""
    global allow_debug

    parser = argparse.ArgumentParser(description="TDX Tool")
    parser.add_argument("--list", action="store_true", help="List all Intel TDX module versions")
    parser.add_argument("--update", nargs='?', const=True, metavar='Intel TDX module version', help="Update the Intel TDX module to the specified or newest version")
    parser.add_argument("--allow_debug", action="store_true", help="Allow loading debug mode modules (default: False)")

    args = parser.parse_args()

    allow_debug = args.allow_debug

    modules = get_all_tdx_modules(DEFAULT_MODULE_DIR)
    if not modules:
        print(f"no Intel TDX module found")
        sys.exit(1)

    if args.list:
        list_tdx_modules(modules)
    elif args.update is not None:
        newest_module = find_newest_tdx_module(modules)

        if args.update is True:
            # No module version provided. Install the newest module
            if newest_module:
                update_tdx_module(newest_module)
            else:
                print("No newer Intel TDX module found for update.")
        else:
            # Find the specified module in the modules array
            specified_module = next((module for module in modules if module.version == args.update), None)

            if specified_module is None:
                print(f"Module version {args.update} does not exist.")
                sys.exit(1)

            if specified_module != newest_module:
                print(f"Specified module version {args.update} is not the newest version.")

            update_tdx_module(specified_module)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
