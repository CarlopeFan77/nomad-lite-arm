#!/usr/bin/env python3

import json
import re
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


# --------------------------------------------------
# Formatting
# --------------------------------------------------

def format_size(size_bytes):

    if size_bytes <= 0:
        return "0 B"

    mib = (
        size_bytes
        / 1024
        / 1024
    )

    if mib < 1024:
        return f"{mib:.1f} MiB"

    gib = mib / 1024

    return f"{gib:.2f} GiB"


def format_mib(size_mib):

    if size_mib < 1024:

        return (
            f"{size_mib:.1f} MiB"
        )

    return (
        f"{size_mib / 1024:.2f} GiB"
    )


# --------------------------------------------------
# Configuration loading
# --------------------------------------------------

def load_config_file(config_file):

    try:

        return json.loads(
            config_file.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as error:

        raise ValueError(
            f"{config_file}: "
            f"invalid JSON: {error}"
        ) from error


def load_states():

    states = []

    if not CONFIG_DIR.exists():
        return states

    for config_file in sorted(
        CONFIG_DIR.glob("*.json")
    ):

        try:

            config = load_config_file(
                config_file
            )

        except ValueError:

            # Validation command will report
            # malformed files explicitly.
            continue


        config["_config_file"] = (
            config_file
        )

        states.append(config)

    return states


def find_state(state_id):

    state_id = (
        state_id
        .strip()
        .lower()
    )

    for state in load_states():

        if (
            state.get("id", "")
            .lower()
            == state_id
        ):

            return state

    return None


# --------------------------------------------------
# Packages
# --------------------------------------------------

def package_path(
    state,
    package_name,
):

    package = (
        state
        .get("packages", {})
        .get(package_name)
    )

    if not package:
        return None

    relative_path = package.get(
        "file"
    )

    if not relative_path:
        return None

    return (
        PROJECT_DIR
        / relative_path
    )


def package_info(
    state,
    package_name,
):

    package = (
        state
        .get("packages", {})
        .get(package_name)
    )

    if not package:

        return {
            "configured": False,
            "installed": False,
            "path": None,
            "size": 0,
            "approx_size_mib": 0,
        }


    path = package_path(
        state,
        package_name,
    )

    installed = (
        path is not None
        and path.is_file()
    )


    return {
        "configured": True,

        "installed":
            installed,

        "path":
            path,

        "size":
            (
                path.stat().st_size
                if installed
                else 0
            ),

        "approx_size_mib":
            float(
                package.get(
                    "approx_size_mib",
                    0,
                )
            ),
    }


# --------------------------------------------------
# Profiles
# --------------------------------------------------

def profile_info(
    state,
    profile_name,
):

    profile = (
        state
        .get("profiles", {})
        .get(profile_name)
    )


    if profile is None:
        return None


    package_names = profile.get(
        "packages",
        [],
    )


    packages = {
        name: package_info(
            state,
            name,
        )
        for name in package_names
    }


    installed = (
        bool(package_names)
        and all(
            item["installed"]
            for item in packages.values()
        )
    )


    approx_size_mib = sum(
        item["approx_size_mib"]
        for item in packages.values()
    )


    installed_size = sum(
        item["size"]
        for item in packages.values()
    )


    return {
        "id":
            profile_name,

        "label":
            profile.get(
                "label",
                profile_name.capitalize(),
            ),

        "description":
            profile.get(
                "description",
                "",
            ),

        "install_note":
            profile.get(
                "install_note",
                "",
            ),

        "packages":
            package_names,

        "installed":
            installed,

        "approx_size_mib":
            approx_size_mib,

        "installed_size":
            installed_size,
    }


def state_info(state):

    packages = {}

    for package_name in (
        state
        .get("packages", {})
        .keys()
    ):

        packages[package_name] = (
            package_info(
                state,
                package_name,
            )
        )


    profiles = {}

    for profile_name in (
        state
        .get("profiles", {})
        .keys()
    ):

        profiles[profile_name] = (
            profile_info(
                state,
                profile_name,
            )
        )


    total_installed_size = sum(
        package["size"]
        for package in packages.values()
        if package["installed"]
    )


    return {
        "id":
            state.get("id"),

        "name":
            state.get(
                "name",
                state.get("id"),
            ),

        "state_code":
            state.get(
                "state_code",
                "",
            ),

        "country":
            state.get(
                "country",
                "",
            ),

        "packages":
            packages,

        "profiles":
            profiles,

        "total_installed_size":
            total_installed_size,
    }


# --------------------------------------------------
# List
# --------------------------------------------------

def show_list():

    states = load_states()


    print()
    print("NOMAD Offline Maps")
    print("==================")
    print()


    if not states:

        print(
            "No map states are configured."
        )

        return


    for state in states:

        info = state_info(state)


        heading = info["name"]

        if info["state_code"]:

            heading += (
                f" ({info['state_code']})"
            )


        print(heading)


        for profile in (
            info["profiles"].values()
        ):

            status = (
                "installed"
                if profile["installed"]
                else "not installed"
            )

            size = format_mib(
                profile[
                    "approx_size_mib"
                ]
            )


            print(
                f"  "
                f"{profile['label']:<8} "
                f"{status:<14} "
                f"~{size}"
            )


        print()


# --------------------------------------------------
# State information
# --------------------------------------------------

def show_info(state_id):

    state = find_state(
        state_id
    )


    if state is None:

        print(
            f"Unknown map state: "
            f"{state_id}"
        )

        print()

        print(
            "Run './nomad maps list' "
            "to see configured states."
        )

        return 1


    info = state_info(state)


    print()
    print("NOMAD Map State")
    print("===============")
    print()

    print(
        f"State:   {info['name']}"
    )

    print(
        f"ID:      {info['id']}"
    )


    if info["state_code"]:

        print(
            f"Code:    "
            f"{info['state_code']}"
        )


    print()


    print("Packages")
    print("--------")


    for (
        package_name,
        package,
    ) in info["packages"].items():

        label = (
            package_name.capitalize()
        )


        status = (
            "installed"
            if package["installed"]
            else "not installed"
        )


        print(
            f"{label}: {status}"
        )


        print(
            "  Expected size: "
            + format_mib(
                package[
                    "approx_size_mib"
                ]
            )
        )


        if package["installed"]:

            print(
                "  Actual size:   "
                + format_size(
                    package["size"]
                )
            )


        print(
            "  File:          "
            f"{package['path']}"
        )

        print()


    print("Install profiles")
    print("----------------")


    for profile in (
        info["profiles"].values()
    ):

        status = (
            "installed"
            if profile["installed"]
            else "not installed"
        )


        print(
            f"{profile['label']}: "
            f"{status}"
        )

        print(
            "  Size: "
            + format_mib(
                profile[
                    "approx_size_mib"
                ]
            )
        )


        if profile["description"]:

            print(
                "  "
                + profile[
                    "description"
                ]
            )


        if profile["install_note"]:

            print(
                "  Note: "
                + profile[
                    "install_note"
                ]
            )


        print()


    if (
        info["total_installed_size"]
        > 0
    ):

        print(
            "Total installed map data: "
            + format_size(
                info[
                    "total_installed_size"
                ]
            )
        )


    return 0


# --------------------------------------------------
# Validation
# --------------------------------------------------

def valid_sha256(value):

    return (
        isinstance(
            value,
            str,
        )
        and re.fullmatch(
            r"[0-9a-fA-F]{64}",
            value,
        )
        is not None
    )


def validate_config(
    config,
    config_file,
):

    errors = []


    required_fields = (
        "schema_version",
        "id",
        "name",
        "state_code",
        "country",
        "center",
        "zoom",
        "bounds",
        "max_bounds",
        "packages",
        "profiles",
    )


    for field in required_fields:

        if field not in config:

            errors.append(
                f"missing field: {field}"
            )


    packages = config.get(
        "packages",
        {}
    )

    profiles = config.get(
        "profiles",
        {}
    )


    if not isinstance(
        packages,
        dict,
    ):

        errors.append(
            "packages must be an object"
        )

        packages = {}


    if not isinstance(
        profiles,
        dict,
    ):

        errors.append(
            "profiles must be an object"
        )

        profiles = {}


    for (
        package_name,
        package,
    ) in packages.items():

        if not isinstance(
            package,
            dict,
        ):

            errors.append(
                f"package '{package_name}' "
                "must be an object"
            )

            continue


        for field in (
            "file",
            "minzoom",
            "maxzoom",
            "approx_size_mib",
            "download",
        ):

            if field not in package:

                errors.append(
                    f"package '{package_name}' "
                    f"missing field: {field}"
                )


        download = package.get(
            "download"
        )


        if not isinstance(
            download,
            dict,
        ):

            errors.append(
                f"package '{package_name}' "
                "download must be an object"
            )

            continue


        final_sha256 = (
            download.get(
                "sha256"
            )
        )


        if not valid_sha256(
            final_sha256
        ):

            errors.append(
                f"package '{package_name}' "
                "download.sha256 must be "
                "a 64-character SHA-256 hash"
            )


        parts = download.get(
            "parts"
        )


        if not isinstance(
            parts,
            list,
        ):

            errors.append(
                f"package '{package_name}' "
                "download.parts must be a list"
            )

            continue


        for index, part in enumerate(
            parts,
            start=1,
        ):

            if not isinstance(
                part,
                dict,
            ):

                errors.append(
                    f"package '{package_name}' "
                    f"download part {index} "
                    "must be an object"
                )

                continue


            url = part.get(
                "url"
            )


            if not isinstance(
                url,
                str,
            ) or not url.strip():

                errors.append(
                    f"package '{package_name}' "
                    f"download part {index} "
                    "missing url"
                )


            part_sha256 = (
                part.get(
                    "sha256"
                )
            )


            if not valid_sha256(
                part_sha256
            ):	

                errors.append(
                    f"package '{package_name}' "
                    f"download part {index} "
                    "sha256 must be a "
                    "64-character SHA-256 hash"
                )


    for (
        profile_name,
        profile,
    ) in profiles.items():

        if not isinstance(
            profile,
            dict,
        ):

            errors.append(
                f"profile '{profile_name}' "
                "must be an object"
            )

            continue


        package_names = (
            profile.get(
                "packages"
            )
        )


        if not isinstance(
            package_names,
            list,
        ):

            errors.append(
                f"profile '{profile_name}' "
                "packages must be a list"
            )

            continue


        for package_name in (
            package_names
        ):

            if (
                package_name
                not in packages
            ):

                errors.append(
                    f"profile '{profile_name}' "
                    "references unknown package: "
                    f"{package_name}"
                )


    return errors


def validate_all():

    print()
    print("NOMAD Map Configuration")
    print("=======================")
    print()


    if not CONFIG_DIR.exists():

        print(
            "ERROR: Map configuration "
            "directory does not exist."
        )

        return 1


    config_files = sorted(
        CONFIG_DIR.glob("*.json")
    )


    if not config_files:

        print(
            "ERROR: No map configurations "
            "found."
        )

        return 1


    failed = False


    for config_file in config_files:

        try:

            config = load_config_file(
                config_file
            )

        except ValueError as error:

            print(
                f"FAIL  {config_file.name}"
            )

            print(
                f"      {error}"
            )

            failed = True

            continue


        errors = validate_config(
            config,
            config_file,
        )


        if errors:

            failed = True

            print(
                f"FAIL  {config_file.name}"
            )


            for error in errors:

                print(
                    f"      {error}"
                )

        else:

            print(
                f"OK    {config_file.name}"
            )


    print()


    if failed:

        print(
            "Map configuration "
            "validation failed."
        )

        return 1


    print(
        "All map configurations are valid."
    )

    return 0


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    command = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "list"
    )


    if command == "list":

        show_list()
        return


    if command == "info":

        if len(sys.argv) < 3:

            print(
                "Usage:"
            )

            print(
                "  map-library.py "
                "info STATE"
            )

            raise SystemExit(1)


        raise SystemExit(
            show_info(
                sys.argv[2]
            )
        )


    if command == "validate":

        raise SystemExit(
            validate_all()
        )


    print(
        f"Unknown command: "
        f"{command}"
    )

    raise SystemExit(1)


if __name__ == "__main__":
    main()
