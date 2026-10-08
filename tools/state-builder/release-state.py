#!/usr/bin/env python3

import argparse
import hashlib
import json
import shutil
import subprocess
import sys

from pathlib import Path


PROJECT_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
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


# --------------------------------------------------
# Command helpers
# --------------------------------------------------

def require_command(name):

    if shutil.which(name):
        return

    raise SystemExit(
        f"\nERROR: Required command "
        f"not found: {name}\n"
    )


def run_command(
    command,
    check=True,
):

    result = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    if (
        check
        and result.returncode != 0
    ):

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(
                result.stderr,
                file=sys.stderr,
            )

        raise SystemExit(
            "\nERROR: Command failed:\n  "
            + " ".join(
                str(item)
                for item in command
            )
        )

    return result


# --------------------------------------------------
# Files
# --------------------------------------------------

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
            f"\nERROR: Could not read "
            f"JSON:\n  {path}\n"
            f"  {error}\n"
        ) from error


def sha256_file(path):

    digest = hashlib.sha256()

    with path.open("rb") as file:

        while True:

            chunk = file.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# --------------------------------------------------
# Local state validation
# --------------------------------------------------

def find_config(
    state_id,
    verify_only,
):

    active = (
        CONFIG_DIR
        / f"{state_id}.json"
    )

    wip = (
        WIP_CONFIG_DIR
        / f"{state_id}.json"
    )


    if verify_only:

        if active.is_file():
            return active, False

        if wip.is_file():
            return wip, True

        raise SystemExit(
            "\nERROR: No active or WIP "
            "state configuration found.\n"
        )


    if active.is_file():

        raise SystemExit(
            "\nERROR: State is already "
            "active:\n"
            f"  {active}\n\n"
            "Use --verify-only if you "
            "only want to verify its "
            "existing release.\n"
        )


    if not wip.is_file():

        raise SystemExit(
            "\nERROR: WIP configuration "
            "not found:\n"
            f"  {wip}\n"
        )


    return wip, True


def validate_local_build(
    state_id,
    state_dir,
    manifest,
):

    if (
        manifest.get("state_id")
        != state_id
    ):

        raise SystemExit(
            "\nERROR: Manifest state ID "
            "does not match requested "
            "state.\n"
        )


    print()
    print("Validating local packages")
    print("=========================")
    print()


    for package_name in PACKAGE_NAMES:

        package = (
            manifest
            .get("packages", {})
            .get(package_name)
        )

        if not package:

            raise SystemExit(
                "\nERROR: Manifest is "
                f"missing {package_name}.\n"
            )


        path = (
            state_dir
            / package["file"]
        )

        if not path.is_file():

            raise SystemExit(
                "\nERROR: Package not "
                f"found:\n  {path}\n"
            )


        actual_size = (
            path.stat().st_size
        )

        expected_size = int(
            package["size_bytes"]
        )


        if actual_size != expected_size:

            raise SystemExit(
                "\nERROR: File size "
                f"mismatch for "
                f"{package_name}.\n"
            )


        print(
            f"{package_name}:"
            " checking SHA-256..."
        )

        actual_hash = sha256_file(
            path
        )

        expected_hash = (
            package["sha256"]
            .lower()
        )


        if actual_hash != expected_hash:

            raise SystemExit(
                "\nERROR: SHA-256 "
                f"mismatch for "
                f"{package_name}.\n"
            )


        print(
            f"  PASS  "
            f"{package['size_mib']:.2f} MiB"
        )


# --------------------------------------------------
# GitHub
# --------------------------------------------------

def check_github():

    require_command("gh")

    result = run_command(
        [
            "gh",
            "auth",
            "status",
        ],
        check=False,
    )

    if result.returncode != 0:

        raise SystemExit(
            "\nERROR: GitHub CLI is not "
            "authenticated.\n\n"
            "Run:\n"
            "  gh auth login\n"
        )


def github_repo():

    result = run_command([
        "gh",
        "repo",
        "view",
        "--json",
        "nameWithOwner",
        "--jq",
        ".nameWithOwner",
    ])

    repo = result.stdout.strip()

    if not repo:

        raise SystemExit(
            "\nERROR: Could not determine "
            "GitHub repository.\n"
        )

    return repo


def get_release(
    repo,
    tag,
):

    page = 1

    while True:

        result = run_command(
            [
                "gh",
                "api",
                (
                    f"repos/{repo}/releases"
                    f"?per_page=100&page={page}"
                ),
            ],
            check=False,
        )

        if result.returncode != 0:
            return None

        try:

            releases = json.loads(
                result.stdout
            )

        except json.JSONDecodeError:

            raise SystemExit(
                "\nERROR: GitHub returned "
                "invalid release data.\n"
            )


        if not isinstance(
            releases,
            list,
        ):

            raise SystemExit(
                "\nERROR: Unexpected GitHub "
                "release response.\n"
            )


        for release in releases:

            if (
                release.get("tag_name")
                == tag
            ):

                return release


        if len(releases) < 100:
            return None

        page += 1


def create_draft_release(
    tag,
    state_name,
):

    print()
    print("Creating draft release")
    print("======================")
    print()

    run_command([
        "gh",
        "release",
        "create",
        tag,
        "--draft",
        "--title",
        (
            f"NOMAD {state_name} "
            "Maps v1"
        ),
        "--notes",
        (
            "Offline map packages for "
            f"{state_name} used by "
            "NOMAD Lite ARM. Includes "
            "Basic vector maps, "
            "Terrarium terrain, and "
            "topographic contour tiles."
        ),
    ])


def upload_packages(
    repo,
    tag,
    state_dir,
    manifest,
):

    print()
    print("Uploading packages")
    print("==================")
    print()


    release = get_release(
        repo,
        tag,
    )

    existing_assets = {}

    if release is not None:

        existing_assets = {
            asset["name"]: asset
            for asset in release.get(
                "assets",
                []
            )
        }


    for package_name in PACKAGE_NAMES:

        package = manifest[
            "packages"
        ][package_name]

        path = (
            state_dir
            / package["file"]
        )

        filename = (
            package["file"]
        )

        existing_asset = (
            existing_assets.get(
                filename
            )
        )


        if existing_asset is not None:

            expected_size = int(
                package["size_bytes"]
            )

            remote_size = int(
                existing_asset.get(
                    "size",
                    0,
                )
            )

            expected_digest = (
                "sha256:"
                + package[
                    "sha256"
                ].lower()
            )

            remote_digest = (
                existing_asset.get(
                    "digest"
                )
            )


            size_matches = (
                remote_size
                == expected_size
            )

            digest_matches = (
                remote_digest is None
                or (
                    remote_digest.lower()
                    == expected_digest
                )
            )


            if (
                size_matches
                and digest_matches
            ):

                print(
                    f"{filename}: "
                    "already uploaded; "
                    "skipping."
                )

                continue


        print(
            f"Uploading {package_name}..."
        )

        result = subprocess.run(
            [
                "gh",
                "release",
                "upload",
                tag,
                str(path),
                "--clobber",
            ],
            cwd=PROJECT_DIR,
            check=False,
        )

        if result.returncode != 0:

            raise SystemExit(
                "\nERROR: Upload failed "
                f"for {package_name}.\n\n"
                "The release remains a "
                "draft. Re-run this command "
                "to retry.\n"
            )


# --------------------------------------------------
# Remote verification
# --------------------------------------------------

def verify_remote_assets(
    repo,
    tag,
    manifest,
):

    print()
    print("Verifying GitHub assets")
    print("=======================")
    print()


    release = get_release(
        repo,
        tag,
    )

    if release is None:

        raise SystemExit(
            "\nERROR: Could not read "
            "GitHub release.\n"
        )


    assets = {
        asset["name"]: asset
        for asset in release.get(
            "assets",
            []
        )
    }


    for package_name in PACKAGE_NAMES:

        package = manifest[
            "packages"
        ][package_name]

        filename = package["file"]

        asset = assets.get(
            filename
        )


        if asset is None:

            raise SystemExit(
                "\nERROR: GitHub release "
                f"is missing {filename}.\n"
            )


        expected_size = int(
            package["size_bytes"]
        )

        remote_size = int(
            asset.get("size", 0)
        )


        if remote_size != expected_size:

            raise SystemExit(
                "\nERROR: GitHub size "
                f"mismatch for {filename}.\n"
            )


        expected_digest = (
            "sha256:"
            + package["sha256"].lower()
        )

        remote_digest = (
            asset.get("digest")
        )


        if remote_digest:

            if (
                remote_digest.lower()
                != expected_digest
            ):

                raise SystemExit(
                    "\nERROR: GitHub SHA-256 "
                    f"digest mismatch for "
                    f"{filename}.\n"
                )

            digest_status = (
                "SHA-256 verified"
            )

        else:

            digest_status = (
                "size verified; "
                "GitHub digest unavailable"
            )


        print(
            f"{filename}: PASS"
        )

        print(
            f"  {remote_size:,} bytes"
        )

        print(
            f"  {digest_status}"
        )


    return release


# --------------------------------------------------
# Configuration
# --------------------------------------------------

def update_config(
    config,
    manifest,
    repo,
    tag,
):

    base_url = (
        f"https://github.com/"
        f"{repo}/releases/download/"
        f"{tag}"
    )


    for package_name in PACKAGE_NAMES:

        package = manifest[
            "packages"
        ][package_name]

        config_package = (
            config["packages"][
                package_name
            ]
        )

        config_package[
            "approx_size_mib"
        ] = package["size_mib"]

        sha256 = (
            package["sha256"]
        )

        config_package["download"] = {
            "sha256": sha256,
            "parts": [
                {
                    "url": (
                        f"{base_url}/"
                        f"{package['file']}"
                    ),
                    "sha256": sha256,
                }
            ],
        }


    topo_size = sum(
        manifest["packages"][name][
            "size_mib"
        ]
        for name in PACKAGE_NAMES
    )


    state_name = config["name"]


    if topo_size >= 1024:

        size_text = (
            f"{topo_size / 1024:.2f} GiB"
        )

    else:

        size_text = (
            f"{topo_size:.0f} MiB"
        )


    config[
        "profiles"
    ][
        "topo"
    ][
        "install_note"
    ] = (
        "Large map package. "
        f"Around {size_text} for "
        f"{state_name} and may take "
        "substantial time to download "
        "and install on lightweight "
        "hardware."
    )


    return topo_size


# --------------------------------------------------
# Release publication
# --------------------------------------------------

def publish_release(tag):

    print()
    print("Publishing release")
    print("==================")
    print()

    run_command([
        "gh",
        "release",
        "edit",
        tag,
        "--draft=false",
    ])


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Publish a completed NOMAD "
            "state map build to GitHub."
        )
    )

    parser.add_argument(
        "state",
        help=(
            "State ID, for example "
            "colorado."
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
            "Override GitHub release tag. "
            "Default: maps-STATE-v1"
        ),
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Skip confirmation prompt."
        ),
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Delete the local state build "
            "directory after a successful "
            "release."
        ),
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help=(
            "Verify an existing release "
            "without changing GitHub or "
            "the state configuration."
        ),
    )

    args = parser.parse_args()


    state_id = (
        args.state
        .strip()
        .lower()
    )

    tag = (
        args.tag
        or f"maps-{state_id}-v1"
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

    manifest_file = (
        state_dir
        / "build-manifest.json"
    )


    if not manifest_file.is_file():

        raise SystemExit(
            "\nERROR: Build manifest "
            "not found:\n"
            f"  {manifest_file}\n"
        )


    config_file, is_wip = (
        find_config(
            state_id,
            args.verify_only,
        )
    )

    config = read_json(
        config_file
    )

    manifest = read_json(
        manifest_file
    )


    if config.get("id") != state_id:

        raise SystemExit(
            "\nERROR: Configuration "
            "state ID mismatch.\n"
        )


    validate_local_build(
        state_id,
        state_dir,
        manifest,
    )


    check_github()

    repo = github_repo()


    print()
    print("NOMAD State Release")
    print("===================")
    print()
    print(
        f"State:   {config['name']}"
    )
    print(
        f"Repo:    {repo}"
    )
    print(
        f"Tag:     {tag}"
    )
    print(
        f"Build:   {state_dir}"
    )


    existing_release = (
        get_release(
            repo,
            tag,
        )
    )


    if args.verify_only:

        if existing_release is None:

            raise SystemExit(
                "\nERROR: Release does "
                "not exist.\n"
            )

        verify_remote_assets(
            repo,
            tag,
            manifest,
        )

        print()
        print(
            "PASS: Existing release "
            "verified."
        )

        return


    if (
        existing_release is not None
        and not existing_release.get(
            "draft",
            False,
        )
    ):

        raise SystemExit(
            "\nERROR: A published release "
            f"already exists for {tag}.\n\n"
            "Nothing was changed.\n"
        )


    if not args.yes:

        print()
        answer = input(
            "Publish this state? [y/N]: "
        )

        if answer.strip().lower() not in (
            "y",
            "yes",
        ):

            print(
                "\nRelease cancelled."
            )

            return


    if existing_release is None:

        create_draft_release(
            tag,
            config["name"],
        )

    else:

        print()
        print(
            "Existing draft release "
            "found. Continuing upload."
        )


    upload_packages(
        repo,
        tag,
        state_dir,
        manifest,
    )


    verify_remote_assets(
        repo,
        tag,
        manifest,
    )


    topo_size = update_config(
        config,
        manifest,
        repo,
        tag,
    )


    config_file.write_text(
        json.dumps(
            config,
            indent=4,
        )
        + "\n",
        encoding="utf-8",
    )


    print()
    print(
        "Updated WIP configuration:"
    )
    print(
        f"  {config_file}"
    )

    print(
        f"Topo total: "
        f"{topo_size:.2f} MiB"
    )


    publish_release(
        tag
    )


    active_config = (
        CONFIG_DIR
        / f"{state_id}.json"
    )


    config_file.replace(
        active_config
    )


    print()
    print("Release complete")
    print("================")
    print()
    print(
        f"Published: {tag}"
    )
    print(
        "Active config:"
    )
    print(
        f"  {active_config}"
    )


    if args.clean:

        print()
        print(
            "Removing local build:"
        )
        print(
            f"  {state_dir}"
        )

        shutil.rmtree(
            state_dir
        )


    print()
    print(
        "Next:"
    )
    print(
        f"  git add "
        f"{active_config.relative_to(PROJECT_DIR)}"
    )
    print(
        f'  git commit -m '
        f'"feat: add '
        f'{config["name"]} offline maps"'
    )
    print(
        "  git push"
    )


if __name__ == "__main__":
    main()
