#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path


PROJECT_DIR = (
    Path(__file__).resolve().parent.parent
)

BASE_URL = (
    "https://download.geofabrik.de/"
    "north-america/us/"
)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download a Geofabrik Shortbread "
            "vector map for a NOMAD state."
        )
    )

    parser.add_argument(
        "state",
        help=(
            "State ID, for example "
            "wyoming or montana."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output path.",
    )

    args = parser.parse_args()

    state_id = (
        args.state
        .strip()
        .lower()
    )

    url = (
        BASE_URL
        + state_id
        + "-shortbread-1.0.mbtiles"
    )

    if args.output is None:

        output_file = (
            PROJECT_DIR
            / "data"
            / "maps"
            / state_id
            / "basic.mbtiles"
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

    partial = output_file.with_name(
        output_file.name + ".partial"
    )

    print()
    print("NOMAD Basic Map Downloader")
    print("==========================")
    print()
    print(f"State:  {state_id}")
    print(f"Source: {url}")
    print(f"Output: {output_file}")
    print()

    command = [
        "curl",
        "--fail",
        "--location",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "--continue-at",
        "-",
        "--progress-bar",
        "--output",
        str(partial),
        url,
    ]

    result = subprocess.run(
        command,
        check=False,
    )

    if result.returncode != 0:

        raise SystemExit(
            "Basic map download failed."
        )

    partial.replace(
        output_file
    )

    size_mib = (
        output_file.stat().st_size
        / 1024
        / 1024
    )

    print()
    print(
        f"Downloaded: {size_mib:.1f} MiB"
    )

    print(
        "PASS: Basic map package "
        "downloaded."
    )


if __name__ == "__main__":
    main()
