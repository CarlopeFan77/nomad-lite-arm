#!/usr/bin/env python3

import argparse
import hashlib
import json
import shutil
import subprocess
import sys

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path


PROJECT_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

SCRIPTS_DIR = (
    PROJECT_DIR
    / "scripts"
)

CONFIG_DIR = (
    PROJECT_DIR
    / "config"
    / "maps"
)

WIP_CONFIG_DIR = (
    CONFIG_DIR
    / "wip"
)

DEFAULT_BUILD_ROOT = (
    Path.home()
    / "nomad-build"
)


# --------------------------------------------------
# Formatting
# --------------------------------------------------

def format_mib(size_bytes):

    return (
        size_bytes
        / 1024
        / 1024
    )


def sha256_file(path):

    digest = hashlib.sha256()

    with path.open("rb") as file:

        while True:

            chunk = file.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# --------------------------------------------------
# Configuration
# --------------------------------------------------

def load_state(state_id):

    config_file = (
        CONFIG_DIR
        / f"{state_id}.json"
    )

    if not config_file.is_file():

        wip_config_file = (
            WIP_CONFIG_DIR
            / f"{state_id}.json"
        )

        if wip_config_file.is_file():

            config_file = (
                wip_config_file
            )

        else:

            raise SystemExit(
                "\nERROR: State configuration "
                "not found in active or WIP maps:\n"
                f"  {config_file}\n"
                f"  {wip_config_file}\n"
            )

    try:

        state = json.loads(
            config_file.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as error:

        raise SystemExit(
            "\nERROR: Invalid state "
            f"configuration:\n  {error}\n"
        ) from error

    return (
        config_file,
        state,
    )


# --------------------------------------------------
# Dependency checks
# --------------------------------------------------

def check_command(name):

    if shutil.which(name):
        return

    raise SystemExit(
        f"\nERROR: Required command "
        f"not found: {name}\n"
    )


def check_dependencies():

    commands = (
        "curl",
        "gdalinfo",
        "ogr2ogr",
        "tippecanoe",
        "tile-join",
    )

    for command in commands:
        check_command(command)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from osgeo import gdal; "
                "print(gdal.VersionInfo())"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:

        raise SystemExit(
            "\nERROR: Python GDAL bindings "
            "are not available.\n"
        )


# --------------------------------------------------
# Commands
# --------------------------------------------------

def run_stage(
    title,
    command,
):

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)
    print()

    print(
        "Command:",
        " ".join(
            str(item)
            for item in command
        ),
    )

    print()

    result = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        check=False,
    )

    if result.returncode != 0:

        raise SystemExit(
            "\nERROR: Stage failed:\n"
            f"  {title}\n"
        )


# --------------------------------------------------
# Manifest
# --------------------------------------------------

def build_manifest(
    state,
    state_dir,
):

    packages = {}

    for package_name in (
        "basic",
        "terrain",
        "contours",
    ):

        path = (
            state_dir
            / f"{package_name}.mbtiles"
        )

        if not path.is_file():
            continue

        size_bytes = (
            path.stat().st_size
        )

        packages[package_name] = {
            "file": path.name,
            "size_bytes": size_bytes,
            "size_mib": round(
                format_mib(
                    size_bytes
                ),
                2,
            ),
            "sha256": sha256_file(
                path
            ),
        }

    return {
        "schema_version": 1,
        "state_id": state["id"],
        "state_name": state["name"],
        "generated_at": (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        ),
        "packages": packages,
    }


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Build NOMAD Basic, terrain, "
            "and contour packages for a state."
        )
    )

    parser.add_argument(
        "state",
        help=(
            "State configuration ID, "
            "for example rhode-island."
        ),
    )

    parser.add_argument(
        "--build-root",
        type=Path,
        default=DEFAULT_BUILD_ROOT,
        help=(
            "Build workspace root. "
            "Default: ~/nomad-build"
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help=(
            "Terrain download workers. "
            "Default: 4"
        ),
    )

    args = parser.parse_args()

    state_id = (
        args.state
        .strip()
        .lower()
    )

    (
        config_file,
        state,
    ) = load_state(
        state_id
    )

    check_dependencies()

    build_root = (
        args.build_root
        .expanduser()
        .resolve()
    )

    state_dir = (
        build_root
        / state_id
    )

    work_dir = (
        state_dir
        / "work"
    )

    package_work_dir = (
        work_dir
        / "package"
    )

    state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("NOMAD State Builder")
    print("===================")
    print()
    print(
        f"State:      "
        f"{state['name']}"
    )
    print(
        f"State ID:   "
        f"{state_id}"
    )
    print(
        f"Config:     "
        f"{config_file}"
    )
    print(
        f"Build dir:  "
        f"{state_dir}"
    )
    print(
        f"Workers:    "
        f"{args.workers}"
    )

    terrain_package = (
        state
        .get("packages", {})
        .get("terrain", {})
    )

    terrain_zoom = int(
        terrain_package.get(
            "maxzoom",
            12,
        )
    )

    basic_file = (
        state_dir
        / "basic.mbtiles"
    )

    terrain_file = (
        state_dir
        / "terrain.mbtiles"
    )

    elevation_file = (
        work_dir
        / (
            f"{state_id}"
            f"-elevation-ft-z"
            f"{terrain_zoom}.tif"
        )
    )

    contour_source = (
        work_dir
        / (
            f"{state_id}"
            "-contours.gpkg"
        )
    )

    contour_file = (
        state_dir
        / "contours.mbtiles"
    )


    if basic_file.is_file():

        print()
        print("=" * 60)
        print("1/5 Basic map")
        print("=" * 60)
        print()
        print(
            "Using existing Basic map:"
        )
        print(
            f"  {basic_file}"
        )

    else:

        run_stage(
            "1/5 Download Basic map",
            [
                sys.executable,
                str(
                    SCRIPTS_DIR
                    / "download-basic-map.py"
                ),
                state_id,
                "--output",
                str(basic_file),
            ],
        )


    run_stage(
        "2/5 Download terrain",
        [
            sys.executable,
            str(
                SCRIPTS_DIR
                / "download-terrain.py"
            ),
            state_id,
            "--workers",
            str(args.workers),
            "--output",
            str(terrain_file),
        ],
    )


    run_stage(
        "3/5 Decode terrain",
        [
            sys.executable,
            str(
                SCRIPTS_DIR
                / "decode-terrain.py"
            ),
            state_id,
            "--input",
            str(terrain_file),
            "--output",
            str(elevation_file),
        ],
    )


    run_stage(
        "4/5 Generate contours",
        [
            sys.executable,
            str(
                SCRIPTS_DIR
                / "generate-contours.py"
            ),
            state_id,
            "--input",
            str(elevation_file),
            "--output",
            str(contour_source),
        ],
    )


    run_stage(
        "5/5 Package contours",
        [
            sys.executable,
            str(
                SCRIPTS_DIR
                / "package-contours.py"
            ),
            state_id,
            "--input",
            str(contour_source),
            "--output",
            str(contour_file),
            "--work-dir",
            str(package_work_dir),
        ],
    )


    print()
    print("=" * 60)
    print("Calculating package hashes")
    print("=" * 60)

    manifest = build_manifest(
        state,
        state_dir,
    )

    manifest_file = (
        state_dir
        / "build-manifest.json"
    )

    manifest_file.write_text(
        json.dumps(
            manifest,
            indent=4,
        )
        + "\n",
        encoding="utf-8",
    )


    print()
    print("Build complete")
    print("==============")
    print()

    for (
        package_name,
        package,
    ) in manifest[
        "packages"
    ].items():

        print(
            f"{package_name.capitalize()}:"
        )

        print(
            "  Size:   "
            f"{package['size_mib']:.2f} MiB"
        )

        print(
            "  SHA256: "
            f"{package['sha256']}"
        )

    print()

    print(
        f"Manifest:\n  "
        f"{manifest_file}"
    )

    print()

    print(
        "Build files remain outside "
        "the Git repository."
    )


if __name__ == "__main__":
    main()
