<!-- Copyright (C) 2025 Intel Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom
the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

SPDX-License-Identifier: MIT -->


## Table of Contents
- [Repository Overview](#repository-overview)
- [How to Use](#how-to-use)
  - [Prerequisites](#prerequisites)
  - [Functionalities](#functionalities)
- [Important Notes](#important-notes)
- [License](#license)

# Intel TDX Module Binaries Repository

Welcome to the **Intel TDX Module Binaries** repository. This repository is designed to facilitate the re-installation of the Intel TDX module on Linux operating systems without requiring a platform reboot (Intel TDX Module update). This approach addresses the growing size of the Intel TDX module and aligns with Cloud Service Provider (CSP) requirements for minimal downtime during updates.

## Repository Overview

This repository offers a streamlined solution for updating the Intel TDX module directly from the Linux OS, focusing on the case when such an update can be done in TD-Preserving way, i.e. by pausing the running TDs, performing the Intel TDX module update and resuming the TDs. The `version_select_and_load.py` script facilitates this process by automatically selecting the most suitable Intel TDX module version based on platform compatibility, while also allowing users to specify a desired version. Additionally, the repository contains released Intel TDX module binaries along with their signature structures, and Intel TDX module blob files — single Linux-compatible files created from the corresponding Intel TDX module binaries and their signature. The `blob_join.sh` script is provided to combine the Intel TDX module binary with its sigstruct into a single blob file, enabling users to verify the validity of the blob.
The `version_select_and_load.py` must work with WIP kernel interfaces to support TD-Preserving. The kernel patches will be submitted to the Linux Kernel Mailing List (LKML) soon and  the `version_select_and_load.py` serves as the user of the kernel patch.

## How to Use

### Prerequisites

- Linux operating system
- Git installed on your system

### Functionalities

**Clone the Repository**:
   - Run the following command to clone the repository and navigate into it:
     ```
     git clone https://github.com/intel/tdx-module-binaries.git
     cd tdx-module-binaries
     ```

**Select and Load Intel TDX Module**:
   - Use the `version_select_and_load.py` script to initiate a Intel TDX Module update. The script will select the most appropriate version or use a specified version, ensuring compatibility. The necessary Intel TDX Module blobs can be found under the `joined_files` directory. Blob’s structure is described in ‘blob_structure.txt’.
     ```
     ./version_select_and_load.py [options]
     ```

**Create Intel TDX Module Blob**:
   - Use the `blob_join.sh` script to create a Linux-style Intel TDX module blob from separate files. The resulting blobs can be found in the `joined_files` directory.
     ```
     ./blob_join.sh <path_to_bin> <path_to_sigstruct>
     ```

## Important Notes

- The repository includes a `mapping_file.json` that encodes TD-Preserving limitations and is used by the `version_select_and_load.py` tool.
  
- Intel TDX module limitations for TD-Preserving update:
  
  | Intel TDX Module to be Updated | Minimum Version of Existing Running Intel TDX Module | Supported SEAMLDR Versions          |
  |--------------------------------|------------------------------------------------------|-------------------------------------|
  | 1.5.01                         | 1.5.01                                               | 1.5.00                              |
  | 1.5.05                         | 1.5.01                                               | 1.5.00, 2.0.00                      |
  | 1.5.06                         | 1.5.01                                               | 1.5.00, 2.0.00                      |

- Performing TD Preserving during a TD Build operation might result in a corrupted TD hash in the TD attestation report. Until fixed in a future Intel TDX module update, a host VMM can avoid the problem by not conducting a TD Preserving Update while TD Build operation is in progress.
- For access to the source code of the Intel TDX modules, please visit the public repository at [Intel TDX Module Source Code](https://github.com/intel/tdx-module).

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file located in the root directory.

Additionally, the Intel TDX Module binaries are licensed under the terms specified in the [BINARIES_LICENSE](BINARIES_LICENSE) file, also located in the root directory. Please review these files for more information regarding the usage and distribution of the software and binaries.