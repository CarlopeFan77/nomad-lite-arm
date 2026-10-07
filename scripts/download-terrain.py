#!/usr/bin/env python3

import argparse
import json
import math
import sqlite3
import time
import urllib.error
import urllib.request

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from pathlib import Path


PROJECT_DIR = (
    Path(__file__).resolve().parent.parent
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

TERRAIN_URL = (
    "https://s3.amazonaws.com/"
    "elevation-tiles-prod/"
    "terrarium/{z}/{x}/{y}.png"
)


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
                "State configuration not found "
                "in active or WIP maps:\n"
                f"  {config_file}\n"
                f"  {wip_config_file}"
            )

    try:

        state = json.loads(
            config_file.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as error:

        raise SystemExit(
            f"Invalid JSON in {config_file}: "
            f"{error}"
        ) from error

    required = (
        "id",
        "name",
        "center",
        "bounds",
        "packages",
    )

    for key in required:

        if key not in state:

            raise SystemExit(
                "State configuration missing "
                f"required field: {key}"
            )

    terrain = (
        state
        .get("packages", {})
        .get("terrain")
    )

    if not terrain:

        raise SystemExit(
            f"{state['name']} does not define "
            "a terrain package."
        )

    if not terrain.get("file"):

        raise SystemExit(
            "Terrain package does not define "
            "a file path."
        )

    return state


def lon_to_x(lon, zoom):

    n = 2 ** zoom

    return int(
        math.floor(
            (lon + 180.0)
            / 360.0
            * n
        )
    )


def lat_to_y(lat, zoom):

    n = 2 ** zoom

    lat_rad = math.radians(lat)

    return int(
        math.floor(
            (
                1.0
                - math.asinh(
                    math.tan(lat_rad)
                )
                / math.pi
            )
            / 2.0
            * n
        )
    )


def xyz_to_tms_y(y, zoom):

    return (
        (2 ** zoom - 1)
        - y
    )


def tile_range(
    bounds,
    zoom,
):

    (
        west,
        south,
        east,
        north,
    ) = bounds

    x_min = lon_to_x(
        west,
        zoom,
    )

    x_max = lon_to_x(
        east,
        zoom,
    )

    y_min = lat_to_y(
        north,
        zoom,
    )

    y_max = lat_to_y(
        south,
        zoom,
    )

    return (
        x_min,
        x_max,
        y_min,
        y_max,
    )


def count_tiles(
    bounds,
    max_zoom,
):

    total = 0

    for zoom in range(
        0,
        max_zoom + 1,
    ):

        (
            x_min,
            x_max,
            y_min,
            y_max,
        ) = tile_range(
            bounds,
            zoom,
        )

        total += (
            (x_max - x_min + 1)
            *
            (y_max - y_min + 1)
        )

    return total


def create_database(
    connection,
    state,
    max_zoom,
):

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            name TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiles (
            zoom_level INTEGER,
            tile_column INTEGER,
            tile_row INTEGER,
            tile_data BLOB
        )
        """
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        tile_index
        ON tiles (
            zoom_level,
            tile_column,
            tile_row
        )
        """
    )

    (
        west,
        south,
        east,
        north,
    ) = state["bounds"]

    (
        center_lon,
        center_lat,
    ) = state["center"]

    metadata = {
        "name":
            f"NOMAD {state['name']} Terrain",

        "type":
            "overlay",

        "version":
            "1.0",

        "description":
            (
                "Terrarium elevation tiles "
                f"for offline {state['name']} "
                "terrain"
            ),

        "format":
            "png",

        "bounds":
            (
                f"{west},"
                f"{south},"
                f"{east},"
                f"{north}"
            ),

        "center":
            (
                f"{center_lon},"
                f"{center_lat},"
                f"{state.get('zoom', 6.5)}"
            ),

        "minzoom":
            "0",

        "maxzoom":
            str(max_zoom),

        "encoding":
            "terrarium",

        "attribution":
            (
                "Elevation data from "
                "Mapzen / Tilezen terrain tiles"
            ),
    }

    for name, value in metadata.items():

        connection.execute(
            """
            INSERT OR REPLACE
            INTO metadata (
                name,
                value
            )
            VALUES (?, ?)
            """,
            (
                name,
                value,
            ),
        )

    connection.commit()


def tile_exists(
    connection,
    zoom,
    x,
    y,
):

    tms_y = xyz_to_tms_y(
        y,
        zoom,
    )

    result = connection.execute(
        """
        SELECT 1
        FROM tiles
        WHERE zoom_level = ?
          AND tile_column = ?
          AND tile_row = ?
        LIMIT 1
        """,
        (
            zoom,
            x,
            tms_y,
        ),
    ).fetchone()

    return result is not None


def download_tile(
    zoom,
    x,
    y,
):

    url = TERRAIN_URL.format(
        z=zoom,
        x=x,
        y=y,
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "NOMAD-Lite-ARM/"
                "terrain-downloader"
        },
    )

    for attempt in range(1, 4):

        try:

            with urllib.request.urlopen(
                request,
                timeout=30,
            ) as response:

                data = response.read()

            if not data.startswith(
                b"\x89PNG\r\n\x1a\n"
            ):

                raise ValueError(
                    "Downloaded data is not PNG"
                )

            return (
                zoom,
                x,
                y,
                data,
                None,
            )

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ValueError,
        ) as error:

            if attempt < 3:
                time.sleep(attempt)

            else:

                return (
                    zoom,
                    x,
                    y,
                    None,
                    str(error),
                )


def save_tile(
    connection,
    zoom,
    x,
    y,
    data,
):

    tms_y = xyz_to_tms_y(
        y,
        zoom,
    )

    connection.execute(
        """
        INSERT OR REPLACE
        INTO tiles (
            zoom_level,
            tile_column,
            tile_row,
            tile_data
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            zoom,
            x,
            tms_y,
            data,
        ),
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download Terrarium elevation "
            "tiles for a NOMAD map state."
        )
    )

    parser.add_argument(
        "state",
        help=(
            "State configuration ID, "
            "for example: wyoming"
        ),
    )

    parser.add_argument(
        "--max-zoom",
        type=int,
        default=None,
        help=(
            "Override terrain maximum "
            "zoom level."
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help=(
            "Concurrent downloads "
            "(default: 4)"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Override output MBTiles path."
        ),
    )

    args = parser.parse_args()

    state_id = (
        args.state
        .strip()
        .lower()
    )

    state = load_state(
        state_id
    )

    terrain = (
        state["packages"]["terrain"]
    )

    configured_max_zoom = int(
        terrain.get(
            "maxzoom",
            12,
        )
    )

    max_zoom = (
        args.max_zoom
        if args.max_zoom is not None
        else configured_max_zoom
    )

    if not 0 <= max_zoom <= 15:

        raise SystemExit(
            "max zoom must be "
            "between 0 and 15"
        )

    if args.workers < 1:

        raise SystemExit(
            "workers must be at least 1"
        )

    if args.output is None:

        output_file = (
            PROJECT_DIR
            / terrain["file"]
        )

    else:

        output_file = (
            args.output.expanduser()
        )

        if not output_file.is_absolute():

            output_file = (
                PROJECT_DIR
                / output_file
            )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    bounds = state["bounds"]

    expected_tiles = count_tiles(
        bounds,
        max_zoom,
    )

    print()
    print(
        f"NOMAD {state['name']} "
        "Terrain Downloader"
    )

    print(
        "="
        * (
            len(state["name"])
            + 25
        )
    )

    print()

    print(
        f"State:    {state['name']}"
    )

    print(
        f"Output:   {output_file}"
    )

    print(
        f"Max zoom: {max_zoom}"
    )

    print(
        f"Workers:  {args.workers}"
    )

    print(
        f"Tiles:    {expected_tiles:,}"
    )

    print()

    connection = sqlite3.connect(
        output_file
    )

    create_database(
        connection,
        state,
        max_zoom,
    )

    downloaded = 0
    skipped = 0
    failed = 0

    for zoom in range(
        0,
        max_zoom + 1,
    ):

        (
            x_min,
            x_max,
            y_min,
            y_max,
        ) = tile_range(
            bounds,
            zoom,
        )

        coordinates = []

        for x in range(
            x_min,
            x_max + 1,
        ):

            for y in range(
                y_min,
                y_max + 1,
            ):

                if tile_exists(
                    connection,
                    zoom,
                    x,
                    y,
                ):

                    skipped += 1
                    continue

                coordinates.append(
                    (
                        zoom,
                        x,
                        y,
                    )
                )

        print(
            f"Zoom {zoom}: "
            f"{len(coordinates):,} "
            "tiles to download"
        )

        if not coordinates:
            continue

        with ThreadPoolExecutor(
            max_workers=args.workers
        ) as executor:

            futures = [
                executor.submit(
                    download_tile,
                    z,
                    x,
                    y,
                )
                for z, x, y
                in coordinates
            ]

            completed_this_zoom = 0

            for future in as_completed(
                futures
            ):

                (
                    z,
                    x,
                    y,
                    data,
                    error,
                ) = future.result()

                completed_this_zoom += 1

                if data is None:

                    failed += 1

                    print(
                        f"  FAILED "
                        f"{z}/{x}/{y}: "
                        f"{error}"
                    )

                    continue

                save_tile(
                    connection,
                    z,
                    x,
                    y,
                    data,
                )

                downloaded += 1

                if downloaded % 50 == 0:
                    connection.commit()

                if (
                    completed_this_zoom % 100
                    == 0
                    or
                    completed_this_zoom
                    == len(coordinates)
                ):

                    print(
                        "  "
                        f"{completed_this_zoom:,}"
                        "/"
                        f"{len(coordinates):,}"
                    )

        connection.commit()

    total_stored = connection.execute(
        """
        SELECT COUNT(*)
        FROM tiles
        """
    ).fetchone()[0]

    connection.close()

    size_mib = (
        output_file.stat().st_size
        / 1024
        / 1024
    )

    print()
    print(
        "Download complete"
    )

    print(
        "================="
    )

    print(
        f"Downloaded: {downloaded:,}"
    )

    print(
        f"Skipped:    {skipped:,}"
    )

    print(
        f"Failed:     {failed:,}"
    )

    print(
        f"Stored:     {total_stored:,}"
    )

    print(
        f"Size:       {size_mib:.1f} MiB"
    )

    print()

    if failed == 0:

        print(
            "PASS: Terrain package "
            "is complete."
        )

    else:

        print(
            "Some tiles failed."
        )

        print(
            "Run the same command again "
            "to retry only missing tiles."
        )


if __name__ == "__main__":
    main()
