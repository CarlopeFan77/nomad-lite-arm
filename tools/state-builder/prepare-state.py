#!/usr/bin/env python3

import argparse
import json
import sqlite3
import subprocess
import sys

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
# Helpers
# --------------------------------------------------

def state_name_from_id(state_id):

    return (
        state_id
        .replace("-", " ")
        .title()
    )


def read_metadata(
    mbtiles_file,
):

    connection = sqlite3.connect(
        mbtiles_file
    )

    rows = connection.execute(
        """
        SELECT name, value
        FROM metadata
        """
    ).fetchall()

    connection.close()

    return {
        name: value
        for name, value in rows
    }


def parse_number_list(
    value,
    expected,
    label,
):

    try:

        values = [
            float(item.strip())
            for item in value.split(",")
        ]

    except (
        AttributeError,
        ValueError,
    ) as error:

        raise SystemExit(
            f"\nERROR: Invalid {label} "
            "metadata.\n"
        ) from error

    if len(values) != expected:

        raise SystemExit(
            f"\nERROR: Expected {expected} "
            f"values in {label} metadata.\n"
        )

    return values


def expand_bounds(bounds):

    west, south, east, north = bounds

    width = east - west
    height = north - south

    lon_margin = max(
        width * 0.08,
        0.25,
    )

    lat_margin = max(
        height * 0.08,
        0.25,
    )

    return [
        round(
            max(
                -180.0,
                west - lon_margin,
            ),
            6,
        ),
        round(
            max(
                -85.0,
                south - lat_margin,
            ),
            6,
        ),
        round(
            min(
                180.0,
                east + lon_margin,
            ),
            6,
        ),
        round(
            min(
                85.0,
                north + lat_margin,
            ),
            6,
        ),
    ]


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Prepare a new US state for "
            "the NOMAD map build pipeline."
        )
    )

    parser.add_argument(
        "state",
        help=(
            "State ID used by Geofabrik, "
            "for example maine."
        ),
    )

    parser.add_argument(
        "--state-code",
        required=True,
        help=(
            "Two-letter US state code, "
            "for example ME."
        ),
    )

    parser.add_argument(
        "--name",
        default=None,
        help=(
            "Override state display name."
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
        "--force",
        action="store_true",
        help=(
            "Replace an existing WIP "
            "configuration."
        ),
    )

    args = parser.parse_args()


    state_id = (
        args.state
        .strip()
        .lower()
    )

    state_code = (
        args.state_code
        .strip()
        .upper()
    )

    state_name = (
        args.name
        if args.name
        else state_name_from_id(
            state_id
        )
    )


    if len(state_code) != 2:

        raise SystemExit(
            "\nERROR: --state-code must "
            "contain two letters.\n"
        )


    active_config = (
        CONFIG_DIR
        / f"{state_id}.json"
    )

    wip_config = (
        WIP_CONFIG_DIR
        / f"{state_id}.json"
    )


    if active_config.is_file():

        raise SystemExit(
            "\nERROR: This state already "
            "has an active configuration:\n"
            f"  {active_config}\n"
        )


    if (
        wip_config.is_file()
        and not args.force
    ):

        raise SystemExit(
            "\nERROR: WIP configuration "
            "already exists:\n"
            f"  {wip_config}\n\n"
            "Use --force to replace it.\n"
        )


    build_root = (
        args.build_root
        .expanduser()
        .resolve()
    )

    state_dir = (
        build_root
        / state_id
    )

    basic_file = (
        state_dir
        / "basic.mbtiles"
    )


    state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    WIP_CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    print()
    print("NOMAD State Preparation")
    print("=======================")
    print()
    print(
        f"State:     {state_name}"
    )
    print(
        f"State ID:  {state_id}"
    )
    print(
        f"Code:      {state_code}"
    )
    print(
        f"Build dir: {state_dir}"
    )
    print()


    if basic_file.is_file():

        print(
            "Using existing Basic map:"
        )

        print(
            f"  {basic_file}"
        )

    else:

        print(
            "Downloading Basic map..."
        )

        result = subprocess.run(
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
            cwd=PROJECT_DIR,
            check=False,
        )

        if result.returncode != 0:

            raise SystemExit(
                "\nERROR: Basic map "
                "download failed.\n"
            )


    print()
    print(
        "Reading MBTiles metadata..."
    )


    metadata = read_metadata(
        basic_file
    )


    if "bounds" not in metadata:

        raise SystemExit(
            "\nERROR: Basic map does not "
            "contain bounds metadata.\n"
        )


    bounds = parse_number_list(
        metadata["bounds"],
        4,
        "bounds",
    )


    if "center" in metadata:

        center_values = (
            parse_number_list(
                metadata["center"],
                3,
                "center",
            )
        )

        center = [
            center_values[0],
            center_values[1],
        ]

        default_zoom = (
            center_values[2]
        )

    else:

        west, south, east, north = (
            bounds
        )

        center = [
            (west + east) / 2,
            (south + north) / 2,
        ]

        default_zoom = 7.0


    min_zoom = int(
        metadata.get(
            "minzoom",
            0,
        )
    )

    max_zoom = int(
        metadata.get(
            "maxzoom",
            14,
        )
    )


    basic_size_mib = (
        basic_file.stat().st_size
        / 1024
        / 1024
    )


    config = {
        "schema_version": 1,

        "id": state_id,
        "name": state_name,
        "state_code": state_code,
        "country": "US",

        "center": [
            round(center[0], 6),
            round(center[1], 6),
        ],

        "zoom": float(
            default_zoom
        ),

        "bounds": [
            round(value, 6)
            for value in bounds
        ],

        "max_bounds":
            expand_bounds(
                bounds
            ),

        "packages": {
            "basic": {
                "file": (
                    f"data/maps/"
                    f"{state_id}/"
                    "basic.mbtiles"
                ),
                "minzoom": min_zoom,
                "maxzoom": max_zoom,
                "approx_size_mib":
                    round(
                        basic_size_mib,
                        2,
                    ),
            },

            "terrain": {
                "file": (
                    f"data/maps/"
                    f"{state_id}/"
                    "terrain.mbtiles"
                ),
                "minzoom": 0,
                "maxzoom": 12,
                "approx_size_mib": 0.0,
            },

            "contours": {
                "file": (
                    f"data/maps/"
                    f"{state_id}/"
                    "contours.mbtiles"
                ),
                "minzoom": 10,
                "maxzoom": 13,
                "approx_size_mib": 0.0,
            },
        },

        "profiles": {
            "basic": {
                "label": "Basic",
                "description": (
                    "Offline roads, towns, places, "
                    "water, buildings, labels, "
                    "and map scale."
                ),
                "packages": [
                    "basic"
                ],
                "install_note": (
                    "Smallest and fastest "
                    "map option."
                ),
            },

            "topo": {
                "label": "Topo",
                "description": (
                    "Basic maps plus hillshade, "
                    "3D terrain, and 40 ft / "
                    "200 ft elevation contours."
                ),
                "packages": [
                    "basic",
                    "terrain",
                    "contours",
                ],
                "install_note": (
                    "Topo package size will be "
                    "filled after the build."
                ),
            },
        },

        "contour_interval_ft": 40,
        "index_contour_interval_ft": 200,

        "contour_tiles": {
            "minor": {
                "minzoom": 12,
                "maxzoom": 13,
            },
            "major": {
                "minzoom": 10,
                "maxzoom": 13,
            },
        },

        "attribution": {
            "basic":
                "OpenStreetMap contributors",

            "terrain":
                "Mapzen / Tilezen terrain data",
        },
    }


    wip_config.write_text(
        json.dumps(
            config,
            indent=4,
        )
        + "\n",
        encoding="utf-8",
    )


    print()
    print("Preparation complete")
    print("====================")
    print()

    print(
        "Basic map:"
    )

    print(
        f"  {basic_file}"
    )

    print(
        f"  {basic_size_mib:.2f} MiB"
    )

    print()

    print(
        "Bounds:"
    )

    print(
        "  "
        + ", ".join(
            str(value)
            for value in bounds
        )
    )

    print()

    print(
        "Center:"
    )

    print(
        "  "
        + ", ".join(
            str(value)
            for value in center
        )
    )

    print()

    print(
        f"Basic zooms: "
        f"{min_zoom}-{max_zoom}"
    )

    print()

    print(
        "Created WIP configuration:"
    )

    print(
        f"  {wip_config}"
    )


if __name__ == "__main__":
    main()
