#!/usr/bin/env python3
"""Check the delivered interface without requiring a ROS installation."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

EXPECTED_FIELDS = [
    "float32 desired_curvature",
    "float32 desired_speed",
    "bool listen_to_steering",
    "bool listen_to_speed",
]
EXPECTED_SOURCES = {
    "control_interfaces/msg/ControlMsg.msg": "control_interfaces/msg/ControlMsg.msg",
    "control_interfaces/CMakeLists.txt": "control_interfaces/CMakeLists.txt",
    "control_interfaces/package.xml": "control_interfaces/package.xml",
    "control_node_pkg/src/control_publisher_node.cpp":
        "examples/control_node_pkg/src/control_publisher_node.cpp",
    "control_listener_pkg/src/control_listener_node.cpp":
        "examples/control_listener_pkg/src/control_listener_node.cpp",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-source", type=Path, help="Also compare against the private local delivery")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    errors = []
    manifest = json.loads((root / "docs/supplied-source-sha256.json").read_text())
    records = manifest["files"]
    if len(records) != len(EXPECTED_SOURCES) or {
        record["source"]: record["path"] for record in records
    } != EXPECTED_SOURCES:
        errors.append("Source manifest must contain exactly the five authorized supplied files")
    for source, destination in EXPECTED_SOURCES.items():
        target = root / destination
        if not target.is_file():
            errors.append("Missing supplied file: " + destination)
            continue
        record = next((r for r in records if r["path"] == destination), None)
        if record is None or hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
            errors.append("Supplied file differs from recorded SHA-256: " + destination)
        if args.staged_source is not None:
            original = args.staged_source / source
            if not original.is_file() or target.read_bytes() != original.read_bytes():
                errors.append("Supplied file differs from local delivery: " + destination)

    message = root / "control_interfaces/msg/ControlMsg.msg"
    if message.is_file():
        fields = [line.split("#", 1)[0].strip() for line in message.read_text().splitlines()]
        if [field for field in fields if field] != EXPECTED_FIELDS:
            errors.append("ControlMsg fields, types or order differ from the four-field contract")

    readme = (root / "README.md").read_text()
    blocks = re.findall(r"```(?:\w+)?\n(.*?)```", readme, re.DOTALL)
    if not any(block.strip().splitlines() == EXPECTED_FIELDS for block in blocks):
        errors.append("README must contain the exact four-field message definition")
    for phrase in ("control_cmd", "control_interfaces/msg/ControlMsg", "positive = LEFT"):
        if phrase not in readme:
            errors.append("README is missing the contract phrase: " + phrase)

    for package, location in (
        ("control_interfaces", "control_interfaces"),
        ("control_node_pkg", "examples/control_node_pkg"),
        ("control_listener_pkg", "examples/control_listener_pkg"),
    ):
        package_xml = root / location / "package.xml"
        cmake = root / location / "CMakeLists.txt"
        if not package_xml.is_file() or not cmake.is_file():
            errors.append("Required ROS package is missing: " + package)
        elif ET.parse(package_xml).getroot().findtext("name") != package:
            errors.append("Unexpected ROS package name in: " + str(package_xml))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Interface contract, three packages and five verbatim supplied files verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
