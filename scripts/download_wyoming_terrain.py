#!/usr/bin/env python3

import argparse
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


OUTPUT_FILE = Path(
    "data/maps/wyoming-terrain.mbtiles"
)

TERRAIN_URL = (
    "https://s3.amazonaws.com/"
    "elevation-tiles-prod/"
    "terrarium/{z}/{x}/{y}.png"
)


# Wyoming Basic map bounds
WEST = -111.0576
SOUTH = 40.98339
EAST = -103.9413
NORTH = 45.01216

CENTER_LON = -107.49945
CENTER_LAT = 42.997775


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


def tile_range(zoom):
    x_min = lon_to_x(
        WEST,
        zoom,
    )

    x_max = lon_to_x(
        EAST,
        zoom,
    )

    # North is the smaller XYZ Y value.
    y_min = lat_to_y(
        NORTH,
        zoom,
    )

    y_max = lat_to_y(
        SOUTH,
        zoom,
    )

    return (
        x_min,
        x_max,
        y_min,
        y_max,
    )


def count_tiles(max_zoom):
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
        ) = tile_range(zoom)

        total += (
            (x_max - x_min + 1)
            *
            (y_max - y_min + 1)
        )

    return total


def create_database(
    connection,
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

    metadata = {
        "name":
            "NOMAD Wyoming Terrain",

        "type":
            "overlay",

        "version":
            "1.0",

        "description":
            (
                "Terrarium elevation tiles "
                "for offline Wyoming terrain"
            ),

        "format":
            "png",

        "bounds":
            (
                f"{WEST},"
                f"{SOUTH},"
                f"{EAST},"
                f"{NORTH}"
            ),

        "center":
            (
                f"{CENTER_LON},"
                f"{CENTER_LAT},"
                "7"
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
                "NOMAD-Lite-ARM/terrain-downloader"
        },
    )

    for attempt in range(1, 4):

        try:
            with urllib.request.urlopen(
                request,
                timeout=30,
            ) as response:

                data = response.read()

            # PNG magic bytes
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
            "Download Wyoming Terrarium "
            "elevation tiles into MBTiles."
        )
    )

    parser.add_argument(
        "--max-zoom",
        type=int,
        default=12,
        help=(
            "Maximum zoom level "
            "(default: 12)"
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

    args = parser.parse_args()

    if not 0 <= args.max_zoom <= 15:
        raise SystemExit(
            "max zoom must be between 0 and 15"
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    expected_tiles = count_tiles(
        args.max_zoom
    )

    print()
    print(
        "NOMAD Wyoming Terrain Downloader"
    )

    print(
        "================================"
    )

    print()

    print(
        f"Output:   {OUTPUT_FILE}"
    )

    print(
        f"Max zoom: {args.max_zoom}"
    )

    print(
        f"Workers:  {args.workers}"
    )

    print(
        f"Tiles:    {expected_tiles:,}"
    )

    print()

    connection = sqlite3.connect(
        OUTPUT_FILE
    )

    create_database(
        connection,
        args.max_zoom,
    )

    downloaded = 0
    skipped = 0
    failed = 0

    for zoom in range(
        0,
        args.max_zoom + 1,
    ):

        (
            x_min,
            x_max,
            y_min,
            y_max,
        ) = tile_range(zoom)

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
        OUTPUT_FILE.stat().st_size
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
            "PASS: Terrain package is complete."
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
