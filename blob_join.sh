#!/bin/bash

# Copyright (C) 2025 Intel Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom
# the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
# OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

# Validate input arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <path_to_intel_tdx_module_bin> <path_to_intel_tdx_module_sigstruct>"
    exit 1
fi

bin_file="$1"
sigstruct_file="$2"

# Extract version numbers from bin file name
if [[ "$bin_file" =~ tdx_module_([0-9]+)\.([0-9]+)\.([0-9]+)\.bin$ ]]; then
    version_major="${BASH_REMATCH[1]}"
    version_minor="${BASH_REMATCH[2]}"
    version_update="${BASH_REMATCH[3]}"
else
    echo "Error: Unable to extract version numbers from bin file name."
    exit 1
fi

# Print extracted version numbers
echo "Major Version: $version_major"
echo "Minor Version: $version_minor"
echo "Update Version: $version_update"

# Validate file existence
if [ ! -f "$bin_file" ]; then
    echo "Error: File $bin_file does not exist."
    exit 1
fi

if [ ! -f "$sigstruct_file" ]; then
    echo "Error: File $sigstruct_file does not exist."
    exit 1
fi

# Validate sigstruct file size
sigstruct_size=$(stat -c%s "$sigstruct_file")
if [ "$sigstruct_size" -ne 2048 ]; then
    echo "Error: Sigstruct file must be 2KB."
    exit 1
fi

# Create output directory
output_dir="./joined_files/${version_major}.${version_minor}/"
mkdir -p "$output_dir"

# Create output file name
output_file="${output_dir}tdx_module_${version_major}.${version_minor}.${version_update}.blob"

# Write header to blob file
{
    printf '\x00\x01' # Version field (little-endian)
    printf '\x00\x00' # Checksum placeholder
    printf '\x00\x20\x00\x00' # Offset of module
    printf 'TDX-BLOB' # Signature
    printf '\x00\x00\x00\x00' # Length placeholder
    printf '\x00\x00\x00\x00' # resv0
    for ((i=0; i<509; i++)); do
        printf '\x00\x00\x00\x00\x00\x00\x00\x00' # resv1[509]
    done
} > "$output_file"

# Append sigstruct to blob file
cat "$sigstruct_file" >> "$output_file"

# Append reserved fields and module to blob file
{
    for ((i=0; i<256; i++)); do
        printf '\x00\x00\x00\x00\x00\x00\x00\x00' # resv2[256]
    done
    cat "$bin_file" # Module
} >> "$output_file"

# Calculate offset and length
module_offset=$((8192)) # 8KB
module_length=$(stat -c%s "$bin_file")
blob_length=$((module_offset + module_length))

# Ensure blob_length is a valid integer
if ! [[ "$blob_length" =~ ^[0-9]+$ ]]; then
    echo "Error: Blob length is not a valid integer."
    exit 1
fi

# Update length field (little-endian)
length_bytes=$(printf '%08x' "$blob_length" | sed 's/\(..\)\(..\)\(..\)\(..\)/\\x\4\\x\3\\x\2\\x\1/')
echo -e "$length_bytes" | dd of="$output_file" bs=1 seek=16 count=4 conv=notrunc

echo "Calculating checksum..."

# Calculate checksum from the beginning of the file
checksum_actual=0

# Read file as pairs of bytes in hexadecimal
while read -r b1 b2; do
    # If second byte is missing (odd number of bytes), set to 0
    [[ -z $b2 ]] && b2=00
    byte1=$((16#$b1))
    byte2=$((16#$b2))
    uint16_value=$((byte1 + (byte2 << 8)))
    checksum_actual=$(( (checksum_actual + uint16_value) & 0xFFFF ))
done < <(xxd -p -c2 "$output_file" | sed 's/\(..\)\(..\)/\1 \2/')

# Calculate the resulting checksum field
checksum_result=$(( (0x10000 - checksum_actual) & 0xFFFF ))

# Update the checksum field in the blob (little-endian)
checksum_bytes=$(printf '%04x' "$checksum_result" | sed 's/\(..\)\(..\)/\\x\2\\x\1/')
echo -e "$checksum_bytes" | dd of="$output_file" bs=1 seek=2 count=2 conv=notrunc

echo "Blob file created successfully: $output_file"