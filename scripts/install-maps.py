#!/usr/bin/env python3

import hashlib
import json
import shutil
import subprocess
import sys

from pathlib import Path


PROJECT_DIR = (
    Path(__file__).resolve().parent.parent
)

CONFIG_DIR = (
    PROJECT_DIR
    / "config"
    / "maps"
)

DOWNLOAD_DIR = (
    PROJECT_DIR
    / ".run"
    / "map-downloads"
)


# --------------------------------------------------
# Formatting
# --------------------------------------------------

def format_mib(size_mib):

    if size_mib < 1024:
        return f"{size_mib:.1f} MiB"

    return f"{size_mib / 1024:.2f} GiB"


# --------------------------------------------------
# Configuration
# --------------------------------------------------

def load_states():

    states = []

    if not CONFIG_DIR.exists():
        return states

    for config_file in sorted(
        CONFIG_DIR.glob("*.json")
    ):

        config = json.loads(
            config_file.read_text(
                encoding="utf-8"
            )
        )

        states.append(config)

    return states


# --------------------------------------------------
# Package helpers
# --------------------------------------------------

def package_path(package):

    return (
        PROJECT_DIR
        / package["file"]
    )


def package_installed(package):

    return package_path(
        package
    ).is_file()


def profile_size(
    state,
    profile,
):

    total = 0.0

    for package_name in (
        profile["packages"]
    ):

        total += float(
            state["packages"][
                package_name
            ]["approx_size_mib"]
        )

    return total


def additional_size(
    state,
    profile,
):

    total = 0.0

    for package_name in (
        profile["packages"]
    ):

        package = (
            state["packages"][
                package_name
            ]
        )

        if not package_installed(
            package
        ):

            total += float(
                package[
                    "approx_size_mib"
                ]
            )

    return total


def profile_installed(
    state,
    profile,
):

    return all(
        package_installed(
            state["packages"][
                package_name
            ]
        )
        for package_name
        in profile["packages"]
    )


# --------------------------------------------------
# SHA-256 verification
# --------------------------------------------------

def calculate_sha256(path):

    digest = hashlib.sha256()

    with path.open("rb") as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def verify_sha256(
    path,
    expected,
):

    if not path.is_file():
        return False

    actual = calculate_sha256(
        path
    )

    return (
        actual.lower()
        == expected.lower()
    )


# --------------------------------------------------
# Downloads
# --------------------------------------------------

def run_curl(
    url,
    destination,
    resume=False,
):

    command = [
        "curl",
        "--fail",
        "--location",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "--progress-bar",
    ]


    if resume:

        command.extend([
            "--continue-at",
            "-",
        ])


    command.extend([
        "--output",
        str(destination),
        url,
    ])


    return subprocess.run(
        command,
        check=False,
    ).returncode


def download_part(
    url,
    expected_sha256,
    destination,
):

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    if destination.is_file():

        print(
            "      Checking existing "
            "download..."
        )

        if verify_sha256(
            destination,
            expected_sha256,
        ):

            print(
                "      Existing part "
                "verified."
            )

            return


        destination.unlink()


    partial = destination.with_name(
        destination.name
        + ".partial"
    )


    print(
        "      Downloading..."
    )


    resume = partial.is_file()


    result = run_curl(
        url,
        partial,
        resume=resume,
    )


    if (
        result != 0
        and resume
    ):

        print(
            "      Resume failed; "
            "retrying from the beginning."
        )

        partial.unlink(
            missing_ok=True
        )

        result = run_curl(
            url,
            partial,
            resume=False,
        )


    if result != 0:

        raise RuntimeError(
            "download failed"
        )


    print(
        "      Verifying downloaded "
        "part..."
    )


    if not verify_sha256(
        partial,
        expected_sha256,
    ):

        partial.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "downloaded part failed "
            "SHA-256 verification"
        )


    partial.replace(
        destination
    )


    print(
        "      Part verified."
    )


# --------------------------------------------------
# Package installation
# --------------------------------------------------

def install_package(
    state,
    package_name,
):

    package = (
        state["packages"][
            package_name
        ]
    )

    destination = package_path(
        package
    )

    download = package.get(
        "download",
        {},
    )

    final_sha256 = download.get(
        "sha256",
        "",
    )

    parts = download.get(
        "parts",
        [],
    )


    print(
        f"  {package_name.capitalize()}"
    )


    if destination.is_file():

        print(
            "      Existing file found."
        )

        print(
            "      Verifying..."
        )


        if verify_sha256(
            destination,
            final_sha256,
        ):

            print(
                "      Already installed "
                "and verified."
            )

            return


        print(
            "      Existing file failed "
            "verification."
        )

        print(
            "      A verified replacement "
            "will be downloaded."
        )


    if not parts:

        raise RuntimeError(
            "download metadata is "
            "not published"
        )


    package_download_dir = (
        DOWNLOAD_DIR
        / state["id"]
        / package_name
    )

    package_download_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    downloaded_parts = []


    for index, part in enumerate(
        parts,
        start=1,
    ):

        url = part["url"]

        part_sha256 = part[
            "sha256"
        ]


        part_file = (
            package_download_dir
            / f"part-{index:03d}"
        )


        print(
            f"      Part "
            f"{index}/{len(parts)}"
        )


        download_part(
            url,
            part_sha256,
            part_file,
        )


        downloaded_parts.append(
            part_file
        )


    assembled = (
        package_download_dir
        / "assembled.mbtiles"
    )


    assembled.unlink(
        missing_ok=True
    )


    print(
        "      Preparing final file..."
    )


    if len(downloaded_parts) == 1:

        shutil.copyfile(
            downloaded_parts[0],
            assembled,
        )

    else:

        with assembled.open(
            "wb"
        ) as output:

            for part_file in (
                downloaded_parts
            ):

                with part_file.open(
                    "rb"
                ) as source:

                    shutil.copyfileobj(
                        source,
                        output,
                        length=1024 * 1024,
                    )


    print(
        "      Verifying final "
        "SHA-256..."
    )


    if not verify_sha256(
        assembled,
        final_sha256,
    ):

        assembled.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "final package failed "
            "SHA-256 verification"
        )


    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    assembled.replace(
        destination
    )


    print(
        "      Installed successfully."
    )


    shutil.rmtree(
        package_download_dir,
        ignore_errors=True,
    )


# --------------------------------------------------
# Interactive state selection
# --------------------------------------------------

def choose_states(states):

    print()
    print("Offline Maps")
    print("------------")
    print()

    print(
        "Available states:"
    )

    print()


    for index, state in enumerate(
        states,
        start=1,
    ):

        print(
            f"  {index}) "
            f"{state['name']} "
            f"({state['state_code']})"
        )


    print()

    print(
        "Select states to install."
    )

    print(
        "Enter numbers separated by commas,"
    )

    print(
        "or press Enter to skip maps."
    )

    print()


    raw = input("> ").strip()


    if not raw:
        return []


    try:

        numbers = [
            int(item.strip())
            for item in raw.split(",")
            if item.strip()
        ]

    except ValueError:

        print()
        print(
            "Invalid selection."
        )

        raise SystemExit(1)


    selections = []

    seen = set()


    for number in numbers:

        if (
            number < 1
            or number > len(states)
        ):

            print()

            print(
                f"Invalid state number: "
                f"{number}"
            )

            raise SystemExit(1)


        if number in seen:
            continue


        seen.add(number)

        selections.append(
            states[number - 1]
        )


    return selections


# --------------------------------------------------
# Interactive profile selection
# --------------------------------------------------

def choose_profile(state):

    profiles = list(
        state["profiles"].items()
    )


    print()
    print(state["name"])
    print(
        "-" * len(state["name"])
    )
    print()


    for index, (
        profile_id,
        profile,
    ) in enumerate(
        profiles,
        start=1,
    ):

        size = profile_size(
            state,
            profile,
        )

        installed = profile_installed(
            state,
            profile,
        )


        status = (
            " [installed]"
            if installed
            else ""
        )


        print(
            f"  {index}) "
            f"{profile['label']} "
            f"~{format_mib(size)}"
            f"{status}"
        )


        print(
            f"     "
            f"{profile['description']}"
        )


        if profile.get(
            "install_note"
        ):

            print(
                f"     Note: "
                f"{profile['install_note']}"
            )


        print()


    while True:

        raw = input(
            "Choose profile: "
        ).strip()


        try:

            number = int(raw)

        except ValueError:

            print(
                "Enter one of the "
                "profile numbers."
            )

            continue


        if (
            1 <= number <= len(
                profiles
            )
        ):

            profile_id, profile = (
                profiles[number - 1]
            )

            return (
                profile_id,
                profile,
            )


        print(
            "Enter one of the "
            "profile numbers."
        )


# --------------------------------------------------
# Summary
# --------------------------------------------------

def show_summary(plan):

    print()
    print("Map Installation Summary")
    print("========================")
    print()


    total_additional = 0.0


    for (
        state,
        profile_id,
        profile,
    ) in plan:

        full_size = profile_size(
            state,
            profile,
        )

        extra_size = additional_size(
            state,
            profile,
        )


        total_additional += (
            extra_size
        )


        print(
            f"{state['name']} "
            f"— {profile['label']}"
        )

        print(
            "  Package size:      "
            f"~{format_mib(full_size)}"
        )

        print(
            "  Additional needed: "
            f"~{format_mib(extra_size)}"
        )

        print()


    print(
        "Total additional map storage:"
    )

    print(
        f"  ~{format_mib(total_additional)}"
    )


    free_bytes = shutil.disk_usage(
        PROJECT_DIR
    ).free

    free_mib = (
        free_bytes
        / 1024
        / 1024
    )


    print()

    print(
        "Current free space:"
    )

    print(
        f"  {format_mib(free_mib)}"
    )


    if total_additional > free_mib:

        print()

        print(
            "ERROR: There is not enough "
            "free space for this selection."
        )

        return False


    if total_additional == 0:

        print()

        print(
            "All selected map packages "
            "appear to be installed."
        )

        print(
            "They will still be verified "
            "before being skipped."
        )


    return True


# --------------------------------------------------
# Installation queue
# --------------------------------------------------

def process_plan(plan):

    print()
    print("Installing offline maps")
    print("=======================")
    print()


    failures = []


    for state_index, (
        state,
        profile_id,
        profile,
    ) in enumerate(
        plan,
        start=1,
    ):

        print(
            f"[{state_index}/{len(plan)}] "
            f"{state['name']} "
            f"{profile['label']}"
        )


        state_failed = False


        for package_name in (
            profile["packages"]
        ):

            try:

                install_package(
                    state,
                    package_name,
                )

            except Exception as error:

                state_failed = True

                failures.append(
                    (
                        state["name"],
                        package_name,
                        str(error),
                    )
                )

                print(
                    f"      ERROR: {error}"
                )

                print()


        if not state_failed:

            print(
                f"  {state['name']} "
                f"{profile['label']} complete."
            )


        print()


    if failures:

        print(
            "Map installation completed "
            "with errors."
        )

        print()


        for (
            state_name,
            package_name,
            message,
        ) in failures:

            print(
                f"  {state_name} / "
                f"{package_name}: "
                f"{message}"
            )


        return 1


    print(
        "All requested maps installed "
        "successfully."
    )

    return 0


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    if shutil.which(
        "curl"
    ) is None:

        print(
            "ERROR: curl is required "
            "to download map packages."
        )

        return 1


    states = load_states()


    if not states:

        print()
        print(
            "No map states are configured."
        )

        return 0


    selected_states = choose_states(
        states
    )


    if not selected_states:

        print()
        print(
            "Skipping offline maps."
        )

        return 0


    plan = []


    for state in selected_states:

        (
            profile_id,
            profile,
        ) = choose_profile(
            state
        )


        plan.append(
            (
                state,
                profile_id,
                profile,
            )
        )


    if not show_summary(
        plan
    ):

        return 1


    print()

    answer = input(
        "Continue with this map selection? "
        "[y/N] "
    ).strip().lower()


    if answer not in (
        "y",
        "yes",
    ):

        print()
        print(
            "Map installation skipped."
        )

        return 0


    return process_plan(
        plan
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
