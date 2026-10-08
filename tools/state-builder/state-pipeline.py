#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys

from pathlib import Path


PROJECT_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

TOOLS_DIR = (
    Path(__file__)
    .resolve()
    .parent
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

PACKAGE_NAMES = (
    "basic",
    "terrain",
    "contours",
)


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
            str(part)
            for part in command
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
            "\nERROR: Pipeline stopped during:\n"
            f"  {title}\n\n"
            "Fix the problem and run the same "
            "pipeline command again."
        )


def read_json(path):

    try:

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as error:

        raise SystemExit(
            "\nERROR: Could not read:\n"
            f"  {path}\n"
            f"  {error}\n"
        ) from error


def build_complete(
    state_id,
    state_dir,
):

    manifest_file = (
        state_dir
        / "build-manifest.json"
    )

    if not manifest_file.is_file():
        return False

    manifest = read_json(
        manifest_file
    )

    if (
        manifest.get("state_id")
        != state_id
    ):
        return False

    packages = manifest.get(
        "packages",
        {},
    )

    for package_name in PACKAGE_NAMES:

        package = packages.get(
            package_name
        )

        if not package:
            return False

        filename = package.get(
            "file"
        )

        if not filename:
            return False

        if not (
            state_dir
            / filename
        ).is_file():
            return False

    return True


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Prepare, build, and publish a "
            "NOMAD offline map state."
        )
    )

    parser.add_argument(
        "state",
        help=(
            "State ID, for example "
            "new-hampshire."
        ),
    )

    parser.add_argument(
        "--state-code",
        default=None,
        help=(
            "Two-letter state code. "
            "Required for a brand-new state."
        ),
    )

    parser.add_argument(
        "--name",
        default=None,
        help=(
            "Override the display name "
            "during preparation."
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
        "--tag",
        default=None,
        help=(
            "Override the release tag. "
            "Default: maps-STATE-v1"
        ),
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Skip the release confirmation."
        ),
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Delete local build data after "
            "a successful release."
        ),
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help=(
            "Run build-state.py even if a "
            "complete build already exists."
        ),
    )

    args = parser.parse_args()


    state_id = (
        args.state
        .strip()
        .lower()
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

    active_config = (
        CONFIG_DIR
        / f"{state_id}.json"
    )

    wip_config = (
        WIP_CONFIG_DIR
        / f"{state_id}.json"
    )


    print()
    print("NOMAD State Pipeline")
    print("====================")
    print()
    print(
        f"State ID:   {state_id}"
    )
    print(
        f"Build root: {build_root}"
    )


    # --------------------------------------------------
    # Already published
    # --------------------------------------------------

    if active_config.is_file():

        print()
        print(
            "State is already active:"
        )
        print(
            f"  {active_config}"
        )

        if (
            state_dir
            / "build-manifest.json"
        ).is_file():

            print()
            print(
                "Verifying existing release..."
            )

            command = [
                sys.executable,
                str(
                    TOOLS_DIR
                    / "release-state.py"
                ),
                state_id,
                "--build-root",
                str(build_root),
                "--verify-only",
            ]

            if args.tag:
                command.extend([
                    "--tag",
                    args.tag,
                ])

            run_stage(
                "Verify existing release",
                command,
            )

        else:

            print()
            print(
                "No local build remains. "
                "Nothing to do."
            )

        return


    # --------------------------------------------------
    # Prepare
    # --------------------------------------------------

    if wip_config.is_file():

        print()
        print(
            "WIP configuration already "
            "exists; skipping preparation."
        )
        print(
            f"  {wip_config}"
        )

    else:

        if not args.state_code:

            raise SystemExit(
                "\nERROR: --state-code is "
                "required for a new state.\n\n"
                "Example:\n"
                "  --state-code NH\n"
            )

        command = [
            sys.executable,
            str(
                TOOLS_DIR
                / "prepare-state.py"
            ),
            state_id,
            "--state-code",
            args.state_code,
            "--build-root",
            str(build_root),
        ]

        if args.name:

            command.extend([
                "--name",
                args.name,
            ])

        run_stage(
            "1/3 Prepare state",
            command,
        )


    # --------------------------------------------------
    # Build
    # --------------------------------------------------

    if (
        not args.rebuild
        and build_complete(
            state_id,
            state_dir,
        )
    ):

        print()
        print(
            "Complete build already exists; "
            "skipping map generation."
        )
        print(
            f"  {state_dir}"
        )

    else:

        command = [
            sys.executable,
            str(
                TOOLS_DIR
                / "build-state.py"
            ),
            state_id,
            "--build-root",
            str(build_root),
            "--workers",
            str(args.workers),
        ]

        run_stage(
            "2/3 Build state",
            command,
        )


    # --------------------------------------------------
    # Release
    # --------------------------------------------------

    command = [
        sys.executable,
        str(
            TOOLS_DIR
            / "release-state.py"
        ),
        state_id,
        "--build-root",
        str(build_root),
    ]

    if args.tag:

        command.extend([
            "--tag",
            args.tag,
        ])

    if args.yes:

        command.append(
            "--yes"
        )

    if args.clean:

        command.append(
            "--clean"
        )


    run_stage(
        "3/3 Release state",
        command,
    )


    print()
    print("=" * 60)
    print("STATE PIPELINE COMPLETE")
    print("=" * 60)
    print()
    print(
        f"State: {state_id}"
    )
    print(
        "Active configuration:"
    )
    print(
        f"  {active_config}"
    )

    print()
    print(
        "Review the configuration, "
        "then commit it to Git:"
    )

    print()
    print(
        f"  git add "
        f"config/maps/{state_id}.json"
    )

    print(
        f'  git commit -m '
        f'"feat: add '
        f'{state_id.replace("-", " ").title()} '
        f'offline maps"'
    )

    print(
        "  git push"
    )


if __name__ == "__main__":
    main()
