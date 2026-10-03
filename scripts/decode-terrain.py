#!/usr/bin/env python3

import argparse
import json

from pathlib import Path

import numpy as np
from osgeo import gdal


PROJECT_DIR = (
    Path(__file__).resolve().parent.parent
)

CONFIG_DIR = (
    PROJECT_DIR
    / "config"
    / "maps"
)

FEET_PER_METER = 3.280839895013123

STRIPE_HEIGHT = 256


def load_state(state_id):

    config_file = (
        CONFIG_DIR
        / f"{state_id}.json"
    )

    if not config_file.is_file():

        raise SystemExit(
            "State configuration not found: "
            f"{config_file}"
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


def resolve_path(path):

    path = Path(path).expanduser()

    if not path.is_absolute():

        path = (
            PROJECT_DIR
            / path
        )

    return path


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Decode NOMAD Terrarium MBTiles "
            "into an elevation GeoTIFF."
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
        "--input",
        type=Path,
        default=None,
        help=(
            "Override terrain MBTiles input."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Override elevation GeoTIFF "
            "output."
        ),
    )

    parser.add_argument(
        "--zoom",
        type=int,
        default=None,
        help=(
            "Override terrain zoom level."
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

    if args.zoom is None:

        zoom_level = int(
            terrain.get(
                "maxzoom",
                12,
            )
        )

    else:

        zoom_level = args.zoom

    if not 0 <= zoom_level <= 15:

        raise SystemExit(
            "zoom must be between 0 and 15"
        )

    if args.input is None:

        input_file = (
            PROJECT_DIR
            / terrain["file"]
        )

    else:

        input_file = resolve_path(
            args.input
        )

    if args.output is None:

        output_file = (
            PROJECT_DIR
            / "data"
            / "maps"
            / "work"
            / (
                f"{state_id}"
                "-elevation-ft-"
                f"z{zoom_level}.tif"
            )
        )

    else:

        output_file = resolve_path(
            args.output
        )

    gdal.UseExceptions()

    # Keep GDAL memory usage modest for
    # lightweight devices such as Chromebooks.
    gdal.SetConfigOption(
        "GDAL_CACHEMAX",
        "128",
    )

    if not input_file.exists():

        raise SystemExit(
            f"Terrain file not found: "
            f"{input_file}"
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print(
        f"NOMAD {state['name']} "
        "Terrain Decoder"
    )

    print(
        "="
        * (
            len(state["name"])
            + 21
        )
    )

    print()

    print(
        f"State:  {state['name']}"
    )

    print(
        f"Input:  {input_file}"
    )

    print(
        f"Output: {output_file}"
    )

    print(
        f"Zoom:   {zoom_level}"
    )

    print()

    # ---------------------------------------------
    # Open the MBTiles explicitly as RGB.
    # ---------------------------------------------

    source = gdal.OpenEx(
        str(input_file),
        gdal.OF_RASTER,
        open_options=[
            f"ZOOM_LEVEL={zoom_level}",
            "BAND_COUNT=3",
        ],
    )

    if source is None:

        raise SystemExit(
            "Could not open terrain MBTiles."
        )

    width = source.RasterXSize
    height = source.RasterYSize

    print(
        f"Raster: {width:,} × {height:,}"
    )

    print()

    # ---------------------------------------------
    # Create compressed Int16 GeoTIFF.
    #
    # State elevations in feet fit comfortably
    # inside signed 16-bit integer storage.
    # ---------------------------------------------

    driver = gdal.GetDriverByName(
        "GTiff"
    )

    if output_file.exists():

        print(
            "Removing previous output..."
        )

        output_file.unlink()

    destination = driver.Create(
        str(output_file),
        width,
        height,
        1,
        gdal.GDT_Int16,
        options=[
            "TILED=YES",
            "BLOCKXSIZE=256",
            "BLOCKYSIZE=256",
            "COMPRESS=DEFLATE",
            "PREDICTOR=2",
            "BIGTIFF=IF_SAFER",
        ],
    )

    destination.SetGeoTransform(
        source.GetGeoTransform()
    )

    destination.SetProjection(
        source.GetProjection()
    )

    output_band = (
        destination.GetRasterBand(1)
    )

    output_band.SetDescription(
        "Elevation (feet)"
    )

    output_band.SetNoDataValue(
        -32768
    )

    red_band = source.GetRasterBand(1)
    green_band = source.GetRasterBand(2)
    blue_band = source.GetRasterBand(3)

    # ---------------------------------------------
    # Decode Terrarium.
    #
    # meters =
    #   R * 256
    #   + G
    #   + B / 256
    #   - 32768
    #
    # Then convert meters -> feet.
    # ---------------------------------------------

    for y_offset in range(
        0,
        height,
        STRIPE_HEIGHT,
    ):

        rows = min(
            STRIPE_HEIGHT,
            height - y_offset,
        )

        red = red_band.ReadAsArray(
            0,
            y_offset,
            width,
            rows,
        ).astype(
            np.float32
        )

        green = green_band.ReadAsArray(
            0,
            y_offset,
            width,
            rows,
        ).astype(
            np.float32
        )

        blue = blue_band.ReadAsArray(
            0,
            y_offset,
            width,
            rows,
        ).astype(
            np.float32
        )

        elevation_meters = (
            red * 256.0
            + green
            + blue / 256.0
            - 32768.0
        )

        elevation_feet = np.rint(
            elevation_meters
            * FEET_PER_METER
        )

        np.clip(
            elevation_feet,
            -32767,
            32767,
            out=elevation_feet,
        )

        output_band.WriteArray(
            elevation_feet.astype(
                np.int16
            ),
            0,
            y_offset,
        )

        completed = min(
            y_offset + rows,
            height,
        )

        percent = (
            completed
            / height
            * 100
        )

        print(
            "\rDecoded: "
            f"{percent:5.1f}% "
            f"({completed:,}/"
            f"{height:,} rows)",
            end="",
            flush=True,
        )

    print()
    print()

    output_band.FlushCache()

    destination.FlushCache()

    destination = None
    source = None

    size_mib = (
        output_file.stat().st_size
        / 1024
        / 1024
    )

    print(
        "Terrain decoding complete."
    )

    print(
        f"Output size: {size_mib:.1f} MiB"
    )

    print()

    print(
        "PASS: Elevation raster ready "
        "for contour generation."
    )


if __name__ == "__main__":
    main()
