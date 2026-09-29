#!/usr/bin/env python3

import gzip
import math
import sqlite3
from pathlib import Path


MAP_FILE = Path("data/maps/wyoming-basic.mbtiles")


def lonlat_to_xyz(lon, lat, zoom):
    """Convert longitude/latitude to an XYZ tile coordinate."""
    n = 2 ** zoom

    x = int((lon + 180.0) / 360.0 * n)

    lat_rad = math.radians(lat)

    y = int(
        (
            1.0
            - math.asinh(math.tan(lat_rad)) / math.pi
        )
        / 2.0
        * n
    )

    return x, y


def main():
    if not MAP_FILE.exists():
        print(f"ERROR: Map file not found: {MAP_FILE}")
        return

    print(f"Testing: {MAP_FILE}")
    print()

    connection = sqlite3.connect(MAP_FILE)
    cursor = connection.cursor()

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    metadata = dict(
        cursor.execute(
            "SELECT name, value FROM metadata"
        ).fetchall()
    )

    print("Metadata:")
    print(f"  Name:     {metadata.get('name')}")
    print(f"  Format:   {metadata.get('format')}")
    print(f"  Bounds:   {metadata.get('bounds')}")
    print(f"  Center:   {metadata.get('center')}")
    print()

    # --------------------------------------------------
    # Tile counts
    # --------------------------------------------------

    total_tiles = cursor.execute(
        "SELECT COUNT(*) FROM tiles"
    ).fetchone()[0]

    print(f"Total tiles: {total_tiles:,}")
    print()

    print("Tiles by zoom:")

    rows = cursor.execute(
        """
        SELECT zoom_level, COUNT(*)
        FROM tiles
        GROUP BY zoom_level
        ORDER BY zoom_level
        """
    ).fetchall()

    for zoom, count in rows:
        print(f"  z{zoom:2}: {count:,}")

    print()

    # --------------------------------------------------
    # Test the center tile
    # --------------------------------------------------

    center = metadata.get("center")

    if not center:
        print("ERROR: No center metadata found.")
        connection.close()
        return

    lon_text, lat_text, zoom_text = center.split(",")

    lon = float(lon_text)
    lat = float(lat_text)
    zoom = int(float(zoom_text))

    x, xyz_y = lonlat_to_xyz(
        lon,
        lat,
        zoom,
    )

    # MBTiles uses TMS tile-row numbering.
    tms_y = (2 ** zoom - 1) - xyz_y

    print("Center tile test:")
    print(f"  Longitude: {lon}")
    print(f"  Latitude:  {lat}")
    print(f"  Zoom:      {zoom}")
    print(f"  XYZ:       {zoom}/{x}/{xyz_y}")
    print(f"  TMS row:   {tms_y}")

    tile = cursor.execute(
        """
        SELECT tile_data
        FROM tiles
        WHERE zoom_level = ?
          AND tile_column = ?
          AND tile_row = ?
        """,
        (
            zoom,
            x,
            tms_y,
        ),
    ).fetchone()

    print()

    if tile is None:
        print("FAIL: Center tile was not found.")
        connection.close()
        return

    tile_data = tile[0]

    print("Tile found!")
    print(f"Stored size: {len(tile_data):,} bytes")

    if tile_data[:2] == b"\x1f\x8b":
        print("Compression: gzip")

        try:
            uncompressed = gzip.decompress(tile_data)

            print(
                "Uncompressed size: "
                f"{len(uncompressed):,} bytes"
            )

        except gzip.BadGzipFile:
            print("WARNING: gzip header found but decompression failed.")

    else:
        print("Compression: none / raw protobuf")

    print()
    print("PASS: Wyoming MBTiles database looks usable.")

    connection.close()


if __name__ == "__main__":
    main()
