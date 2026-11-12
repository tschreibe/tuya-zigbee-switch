#!/usr/bin/env python3
"""Build a Zigbee OTA upgrade file (ZCL 11.4.2) around a GBL image.

Same flags as `commander-cli ota create`, so the `silabs/ota` make target can
call either. The OTA file is the 56-byte header (field control 0) followed by
one Upgrade Image sub-element (tag 0x0000, u32 length) carrying the GBL; the
bootloader verifies the GBL's own checksum, the header carries identity only.

Usage:
    make_silabs_ota.py --upgrade-image app.gbl \
        --manufacturer-id 4417 --image-type 54179 \
        --firmware-version 0x01020304 --string "My firmware" \
        --outfile out.zigbee
"""

import argparse
import struct
import sys

OTA_FILE_IDENTIFIER = 0x0BEEF11E
HEADER_VERSION = 0x0100
HEADER_LENGTH = 56
ZIGBEE_STACK_VERSION = 0x0002
TAG_UPGRADE_IMAGE = 0x0000


def parse_int(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upgrade-image", required=True, help="GBL file to wrap")
    parser.add_argument("--manufacturer-id", required=True, type=parse_int)
    parser.add_argument("--image-type", required=True, type=parse_int)
    parser.add_argument("--firmware-version", required=True, type=parse_int)
    parser.add_argument("--string", default="", help="32-byte header string")
    parser.add_argument("--outfile", required=True)
    args = parser.parse_args()

    for name, value, bits in (
        ("manufacturer-id", args.manufacturer_id, 16),
        ("image-type", args.image_type, 16),
        ("firmware-version", args.firmware_version, 32),
    ):
        if not 0 <= value < (1 << bits):
            parser.error(f"--{name} out of range for {bits} bits: {value}")

    with open(args.upgrade_image, "rb") as handle:
        gbl = handle.read()

    header_string = args.string.encode()[:32].ljust(32, b"\x00")
    image_size = HEADER_LENGTH + 6 + len(gbl)
    header = struct.pack(
        "<IHHHHHIH32sI",
        OTA_FILE_IDENTIFIER,
        HEADER_VERSION,
        HEADER_LENGTH,
        0,  # field control: no optional header fields
        args.manufacturer_id,
        args.image_type,
        args.firmware_version,
        ZIGBEE_STACK_VERSION,
        header_string,
        image_size,
    )
    sub_element = struct.pack("<HI", TAG_UPGRADE_IMAGE, len(gbl)) + gbl

    with open(args.outfile, "wb") as handle:
        handle.write(header + sub_element)

    print(
        f"wrote {args.outfile}: mfr 0x{args.manufacturer_id:04X} "
        f"type 0x{args.image_type:04X} version 0x{args.firmware_version:08X} "
        f"({image_size} bytes, GBL {len(gbl)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
