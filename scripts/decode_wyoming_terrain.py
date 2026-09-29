#!/usr/bin/env python3

from pathlib import Path

import numpy as np
from osgeo import gdal


INPUT_FILE = Path(
    "data/maps/wyoming-terrain.mbtiles"
)

OUTPUT_FILE = Path(
    "data/maps/work/wyoming-elevation-ft-z12.tif"
)

ZOOM_LEVEL = 12

FEET_PER_METER = 3.280839895013123

STRIPE_HEIGHT = 256


def main():

    gdal.UseExceptions()

    # Keep GDAL's cache modest for the Chromebook.
    gdal.SetConfigOption(
        "GDAL_CACHEMAX",
        "128",
    )

    if not INPUT_FILE.exists():

        raise SystemExit(
            f"Terrain file not found: {INPUT_FILE}"
        )


    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    print()
    print(
        "NOMAD Terrain Decoder"
    )

    print(
        "====================="
    )

    print()

    print(
        f"Input:  {INPUT_FILE}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Zoom:   {ZOOM_LEVEL}"
    )

    print()


    # ---------------------------------------------
    # Open the MBTiles explicitly as z12 RGB.
    # ---------------------------------------------

    source = gdal.OpenEx(

        str(INPUT_FILE),

        gdal.OF_RASTER,

        open_options=[

            f"ZOOM_LEVEL={ZOOM_LEVEL}",

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
    # Wyoming elevation in feet easily fits inside
    # signed 16-bit integer storage.
    # ---------------------------------------------

    driver = gdal.GetDriverByName(
        "GTiff"
    )


    if OUTPUT_FILE.exists():

        print(
            "Removing previous output..."
        )

        OUTPUT_FILE.unlink()


    destination = driver.Create(

        str(OUTPUT_FILE),

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


        # Keep everything valid for Int16.
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
            f"\rDecoded: "
            f"{percent:5.1f}% "
            f"({completed:,}/{height:,} rows)",
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
        OUTPUT_FILE.stat().st_size
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
