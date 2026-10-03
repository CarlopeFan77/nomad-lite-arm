#!/usr/bin/env python3

import argparse
import json

from pathlib import Path

from osgeo import gdal
from osgeo import ogr
from osgeo import osr


PROJECT_DIR = (
    Path(__file__).resolve().parent.parent
)

CONFIG_DIR = (
    PROJECT_DIR
    / "config"
    / "maps"
)


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
        "contour_interval_ft",
        "index_contour_interval_ft",
    )

    for key in required:

        if key not in state:

            raise SystemExit(
                "State configuration missing "
                f"required field: {key}"
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


def create_contour_layer(
    dataset,
    source_band,
    source_srs,
    layer_name,
    interval,
    nodata_value,
):

    print(
        f"Generating {layer_name}: "
        f"{interval} ft interval..."
    )

    layer = dataset.CreateLayer(
        layer_name,
        srs=source_srs,
        geom_type=ogr.wkbLineString,
    )

    if layer is None:

        raise SystemExit(
            f"Could not create layer: "
            f"{layer_name}"
        )

    id_field = ogr.FieldDefn(
        "id",
        ogr.OFTInteger64,
    )

    elevation_field = ogr.FieldDefn(
        "elevation_ft",
        ogr.OFTInteger,
    )

    layer.CreateField(
        id_field
    )

    layer.CreateField(
        elevation_field
    )

    layer_definition = (
        layer.GetLayerDefn()
    )

    id_index = (
        layer_definition
        .GetFieldIndex("id")
    )

    elevation_index = (
        layer_definition
        .GetFieldIndex(
            "elevation_ft"
        )
    )

    use_nodata = (
        1
        if nodata_value is not None
        else 0
    )

    if nodata_value is None:
        nodata_value = 0.0

    result = gdal.ContourGenerate(
        source_band,
        float(interval),
        0.0,
        [],
        use_nodata,
        float(nodata_value),
        layer,
        id_index,
        elevation_index,
    )

    if result != gdal.CE_None:

        raise SystemExit(
            "GDAL contour generation "
            f"failed for {layer_name}."
        )

    feature_count = (
        layer.GetFeatureCount()
    )

    print(
        f"  Created "
        f"{feature_count:,} features"
    )

    return feature_count


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate NOMAD contour "
            "layers from an elevation "
            "GeoTIFF."
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
            "Override elevation "
            "GeoTIFF input."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Override contour "
            "GeoPackage output."
        ),
    )

    parser.add_argument(
        "--zoom",
        type=int,
        default=None,
        help=(
            "Elevation raster zoom "
            "used in the default "
            "input filename."
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
        state
        .get("packages", {})
        .get("terrain", {})
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

    minor_interval = int(
        state[
            "contour_interval_ft"
        ]
    )

    major_interval = int(
        state[
            "index_contour_interval_ft"
        ]
    )

    if minor_interval <= 0:

        raise SystemExit(
            "Minor contour interval "
            "must be greater than zero."
        )

    if major_interval <= 0:

        raise SystemExit(
            "Major contour interval "
            "must be greater than zero."
        )

    if (
        major_interval
        % minor_interval
        != 0
    ):

        raise SystemExit(
            "Major contour interval "
            "must be a multiple of "
            "the minor interval."
        )

    if args.input is None:

        input_file = (
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
                "-contours.gpkg"
            )
        )

    else:

        output_file = resolve_path(
            args.output
        )

    if not input_file.is_file():

        raise SystemExit(
            f"Elevation raster not found: "
            f"{input_file}"
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if output_file.exists():

        print(
            "Removing previous output: "
            f"{output_file}"
        )

        output_file.unlink()

    gdal.UseExceptions()

    print()
    print(
        f"NOMAD {state['name']} "
        "Contour Generator"
    )

    print(
        "="
        * (
            len(state["name"])
            + 22
        )
    )

    print()

    print(
        f"State:    {state['name']}"
    )

    print(
        f"Input:    {input_file}"
    )

    print(
        f"Output:   {output_file}"
    )

    print(
        f"Minor:    "
        f"{minor_interval} ft"
    )

    print(
        f"Major:    "
        f"{major_interval} ft"
    )

    print()

    source = gdal.Open(
        str(input_file),
        gdal.GA_ReadOnly,
    )

    if source is None:

        raise SystemExit(
            "Could not open elevation "
            "raster."
        )

    source_band = (
        source.GetRasterBand(1)
    )

    nodata_value = (
        source_band.GetNoDataValue()
    )

    projection = (
        source.GetProjection()
    )

    source_srs = osr.SpatialReference()

    if projection:

        source_srs.ImportFromWkt(
            projection
        )

    else:

        source_srs = None

    gpkg_driver = (
        ogr.GetDriverByName(
            "GPKG"
        )
    )

    if gpkg_driver is None:

        raise SystemExit(
            "GDAL GeoPackage driver "
            "is unavailable."
        )

    output = (
        gpkg_driver.CreateDataSource(
            str(output_file)
        )
    )

    if output is None:

        raise SystemExit(
            "Could not create contour "
            "GeoPackage."
        )

    minor_count = (
        create_contour_layer(
            output,
            source_band,
            source_srs,
            "minor_contours",
            minor_interval,
            nodata_value,
        )
    )

    major_count = (
        create_contour_layer(
            output,
            source_band,
            source_srs,
            "major_contours",
            major_interval,
            nodata_value,
        )
    )

    output = None
    source = None

    size_mib = (
        output_file.stat().st_size
        / 1024
        / 1024
    )

    print()
    print(
        "Contour generation complete."
    )

    print(
        f"Minor features: "
        f"{minor_count:,}"
    )

    print(
        f"Major features: "
        f"{major_count:,}"
    )

    print(
        f"Output size:    "
        f"{size_mib:.1f} MiB"
    )

    print()

    print(
        "PASS: Contour GeoPackage "
        "is ready for vector tile "
        "packaging."
    )


if __name__ == "__main__":
    main()
