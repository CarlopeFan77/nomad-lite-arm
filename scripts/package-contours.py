#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import tempfile

from pathlib import Path


PROJECT_DIR = (
    Path(__file__).resolve().parent.parent
)

CONFIG_DIR = (
    PROJECT_DIR
    / "config"
    / "maps"
)

RUN_DIR = (
    PROJECT_DIR
    / ".run"
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
        "packages",
        "contour_tiles",
    )

    for key in required:

        if key not in state:

            raise SystemExit(
                "State configuration missing "
                f"required field: {key}"
            )

    contours = (
        state
        .get("packages", {})
        .get("contours")
    )

    if not contours:

        raise SystemExit(
            f"{state['name']} does not define "
            "a contours package."
        )

    if not contours.get("file"):

        raise SystemExit(
            "Contours package does not define "
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


def require_command(command):

    if shutil.which(command) is None:

        raise SystemExit(
            "Required command not found: "
            f"{command}"
        )


def run_command(command):

    print()
    print(
        "  "
        + " ".join(
            str(part)
            for part in command
        )
    )

    subprocess.run(
        command,
        check=True,
    )


def export_layer(
    input_file,
    layer_name,
    output_file,
):

    print()
    print(
        f"Exporting {layer_name}..."
    )

    run_command([
        "ogr2ogr",
        "-f",
        "GeoJSONSeq",
        str(output_file),
        str(input_file),
        layer_name,
    ])


def build_layer(
    source_file,
    output_file,
    layer_name,
    minzoom,
    maxzoom,
):

    print()
    print(
        f"Packaging {layer_name}: "
        f"Z{minzoom}–{maxzoom}"
    )

    run_command([
        "tippecanoe",
        "--force",
        "-o",
        str(output_file),
        "-l",
        layer_name,
        "-Z",
        str(minzoom),
        "-z",
        str(maxzoom),
        str(source_file),
    ])


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Package NOMAD contour layers "
            "into MBTiles."
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
            "Override contour "
            "GeoPackage input."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Override final contour "
            "MBTiles output."
        ),
    )

    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help=(
            "Directory for large temporary "
            "contour packaging files."
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

    require_command(
        "ogr2ogr"
    )

    require_command(
        "tippecanoe"
    )

    require_command(
        "tile-join"
    )

    if args.input is None:

        input_file = (
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

        input_file = resolve_path(
            args.input
        )

    if args.output is None:

        output_file = (
            PROJECT_DIR
            / state["packages"]
            ["contours"]["file"]
        )

    else:

        output_file = resolve_path(
            args.output
        )

    if not input_file.is_file():

        raise SystemExit(
            "Contour GeoPackage not found: "
            f"{input_file}"
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if args.work_dir is None:

        work_dir = RUN_DIR

    else:

        work_dir = resolve_path(
            args.work_dir
        )

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    contour_tiles = (
        state["contour_tiles"]
    )

    minor = (
        contour_tiles["minor"]
    )

    major = (
        contour_tiles["major"]
    )

    minor_minzoom = int(
        minor["minzoom"]
    )

    minor_maxzoom = int(
        minor["maxzoom"]
    )

    major_minzoom = int(
        major["minzoom"]
    )

    major_maxzoom = int(
        major["maxzoom"]
    )

    print()
    print(
        f"NOMAD {state['name']} "
        "Contour Packager"
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

    print()

    print(
        "Minor contours: "
        f"Z{minor_minzoom}–"
        f"{minor_maxzoom}"
    )

    print(
        "Major contours: "
        f"Z{major_minzoom}–"
        f"{major_maxzoom}"
    )

    print(
        f"Work dir: {work_dir}"
    )

    with tempfile.TemporaryDirectory(
        prefix=(
            f"{state_id}-contours-"
        ),
        dir=work_dir,
    ) as temp_dir_name:

        temp_dir = Path(
            temp_dir_name
        )

        minor_geojson = (
            temp_dir
            / "minor.geojsonseq"
        )

        major_geojson = (
            temp_dir
            / "major.geojsonseq"
        )

        minor_mbtiles = (
            temp_dir
            / "minor.mbtiles"
        )

        major_mbtiles = (
            temp_dir
            / "major.mbtiles"
        )

        export_layer(
            input_file,
            "minor_contours",
            minor_geojson,
        )

        export_layer(
            input_file,
            "major_contours",
            major_geojson,
        )

        build_layer(
            minor_geojson,
            minor_mbtiles,
            "minor_contours",
            minor_minzoom,
            minor_maxzoom,
        )

        build_layer(
            major_geojson,
            major_mbtiles,
            "major_contours",
            major_minzoom,
            major_maxzoom,
        )

        if output_file.exists():

            print()
            print(
                "Removing previous output: "
                f"{output_file}"
            )

            output_file.unlink()

        print()
        print(
            "Merging contour layers..."
        )

        run_command([
            "tile-join",
            "--force",
            "-o",
            str(output_file),
            str(major_mbtiles),
            str(minor_mbtiles),
        ])

    if not output_file.is_file():

        raise SystemExit(
            "Contour MBTiles was not "
            "created."
        )

    size_mib = (
        output_file.stat().st_size
        / 1024
        / 1024
    )

    print()
    print(
        "Contour packaging complete."
    )

    print(
        f"Output size: "
        f"{size_mib:.1f} MiB"
    )

    print()

    print(
        "PASS: Contour MBTiles "
        "package is ready."
    )


if __name__ == "__main__":
    main()
