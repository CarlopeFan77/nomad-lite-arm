#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$PROJECT_DIR/scripts"

PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3)"
fi


show_help() {
    echo
    echo "NOMAD Lite ARM"
    echo "================================"
    echo
    echo "Usage:"
    echo "  ./nomad COMMAND"
    echo
    echo "Commands:"
    echo "  start                     Start all NOMAD services"
    echo "  stop                      Stop all NOMAD services"
    echo "  restart                   Restart all NOMAD services"
    echo "  status                    Show all service status"
    echo
    echo "  kiwix start               Start Kiwix"
    echo "  kiwix stop                Stop Kiwix"
    echo "  kiwix status              Show Kiwix status"
    echo
    echo "  education start           Start Kolibri"
    echo "  education stop            Stop Kolibri"
    echo "  education status          Show Kolibri status"
    echo
    echo "  maps start [STATE]        Start Maps for a state"
    echo "  maps stop                 Stop offline Maps"
    echo "  maps restart              Restart offline Maps"
    echo "  maps status               Show Maps status"
    echo "  maps open                 Open Maps in browser"
    echo "  maps logs                 Show recent Maps logs"
    echo "  maps list                 Show configured map states"
    echo "  maps info [STATE]         Show installed map packages"
    echo "  maps validate             Validate map configuration"
    echo
    echo "  system                    Show system information"
    echo "  dashboard                 Start web dashboard"
    echo
    echo "  library list              Show available content"
    echo "  library installed         Show installed content"
    echo "  library info [NAME]       Show collection information"
    echo "  library install [NAME]    Install a collection"
    echo "  library remove [NAME]     Remove a collection"
    echo
    echo "  help                      Show this help"
    echo
}

installed_map_states() {
    "$PYTHON" - "$PROJECT_DIR" <<'PY'
import json
import sys

from pathlib import Path


project_dir = Path(sys.argv[1])

config_dir = (
    project_dir
    / "config"
    / "maps"
)


for config_file in sorted(
    config_dir.glob("*.json")
):

    try:
        state = json.loads(
            config_file.read_text(
                encoding="utf-8"
            )
        )

    except (
        json.JSONDecodeError,
        OSError,
    ):
        continue

    state_id = state.get(
        "id",
        config_file.stem,
    )

    state_name = state.get(
        "name",
        state_id,
    )

    basic = (
        state
        .get("packages", {})
        .get("basic", {})
    )

    relative_path = basic.get(
        "file"
    )

    if not relative_path:
        continue

    basic_file = (
        project_dir
        / relative_path
    )

    if basic_file.is_file():
        print(
            f"{state_id}\t{state_name}"
        )
PY
}


validate_map_state() {
    local state_id="$1"

    "$PYTHON" - \
        "$PROJECT_DIR" \
        "$state_id" <<'PY'
import json
import sys

from pathlib import Path


project_dir = Path(sys.argv[1])

state_id = (
    sys.argv[2]
    .strip()
    .lower()
)

config_file = (
    project_dir
    / "config"
    / "maps"
    / f"{state_id}.json"
)


if not config_file.is_file():

    print(
        f"Unknown map state: {state_id}"
    )

    raise SystemExit(1)


try:

    state = json.loads(
        config_file.read_text(
            encoding="utf-8"
        )
    )

except json.JSONDecodeError:

    print(
        f"Invalid map configuration: "
        f"{config_file}"
    )

    raise SystemExit(1)


basic = (
    state
    .get("packages", {})
    .get("basic", {})
)

relative_path = basic.get(
    "file"
)


if not relative_path:

    print(
        f"{state.get('name', state_id)} "
        "does not define a Basic map."
    )

    raise SystemExit(1)


basic_file = (
    project_dir
    / relative_path
)


if not basic_file.is_file():

    print(
        f"{state.get('name', state_id)} "
        "is configured but not installed."
    )

    raise SystemExit(1)


print(
    state.get(
        "name",
        state_id,
    )
)
PY
}


start_maps() {
    local requested_state="${1:-}"
    local state_id
    local state_name
    local selection
    local entry
    local index
    local -a states=()

    if [[ -n "$requested_state" ]]; then

        state_id="$(
            printf '%s' "$requested_state" \
                | tr '[:upper:]' '[:lower:]'
        )"

        if ! state_name="$(
            validate_map_state "$state_id"
        )"; then
            return 1
        fi

    else

        mapfile -t states < <(
            installed_map_states
        )

        if [[ ${#states[@]} -eq 0 ]]; then
            echo
            echo "No offline map states are installed."
            echo
            echo "Install a map before starting Maps."
            return 1
        fi

        if [[ ${#states[@]} -eq 1 ]]; then

            entry="${states[0]}"
            state_id="${entry%%$'\t'*}"
            state_name="${entry#*$'\t'}"

        else

            echo
            echo "NOMAD Maps"
            echo "================================"
            echo
            echo "Installed map states:"
            echo

            index=1

            for entry in "${states[@]}"; do
                state_name="${entry#*$'\t'}"

                printf \
                    "  %d) %s\n" \
                    "$index" \
                    "$state_name"

                ((index += 1))
            done

            echo

            read -r -p \
                "Choose a state [1-${#states[@]}]: " \
                selection

            if ! [[ "$selection" =~ ^[0-9]+$ ]]; then
                echo
                echo "Invalid selection."
                return 1
            fi

            if (( selection < 1 || selection > ${#states[@]} )); then
                echo
                echo "Invalid selection."
                return 1
            fi

            entry="${states[selection - 1]}"
            state_id="${entry%%$'\t'*}"
            state_name="${entry#*$'\t'}"
        fi
    fi

    echo
    echo "Starting NOMAD Maps"
    echo "State: $state_name"
    echo

    "$SCRIPTS/maps.sh" stop \
        >/dev/null 2>&1 \
        || true

    NOMAD_MAPS_STATE="$state_id" \
        "$SCRIPTS/maps.sh" start

    mkdir -p "$PROJECT_DIR/.run"

    printf '%s\n' "$state_id" \
        > "$PROJECT_DIR/.run/maps.state"
}


case "${1:-help}" in

    start)
        "$SCRIPTS/kiwix.sh" start
        "$SCRIPTS/kolibri.sh" start
        "$SCRIPTS/maps.sh" start
        ;;

    stop)
        "$SCRIPTS/kiwix.sh" stop
        "$SCRIPTS/kolibri.sh" stop
        "$SCRIPTS/maps.sh" stop
        ;;

    restart)
        "$SCRIPTS/kiwix.sh" stop
        "$SCRIPTS/kolibri.sh" stop
        "$SCRIPTS/maps.sh" stop

        "$SCRIPTS/kiwix.sh" start
        "$SCRIPTS/kolibri.sh" start
        "$SCRIPTS/maps.sh" start
        ;;

    status)
        echo
        echo "Kiwix"
        echo "--------------------------------"
        "$SCRIPTS/kiwix.sh" status

        echo
        echo "Kolibri"
        echo "--------------------------------"
        "$SCRIPTS/kolibri.sh" status

        echo
        echo "Maps"
        echo "--------------------------------"
        "$SCRIPTS/maps.sh" status

        echo
        ;;

    kiwix)
        shift
        "$SCRIPTS/kiwix.sh" "$@"
        ;;

    education)
        shift

        case "${1:-}" in

            start|stop|status)
                "$SCRIPTS/kolibri.sh" "$@"
                ;;

            list|info|install)
                "$SCRIPTS/education-library.sh" "$@"
                ;;

            *)
                echo
                echo "Education commands:"
                echo "  ./nomad education start"
                echo "  ./nomad education stop"
                echo "  ./nomad education status"
                echo
                echo "  ./nomad education list"
                echo "  ./nomad education info COURSE"
                echo "  ./nomad education install COURSE"
                echo
                ;;
        esac
        ;;

    system)
        "$SCRIPTS/system-info.sh"
        ;;

    maps)
        shift

        case "${1:-}" in

            start)
                shift
                start_maps "${1:-}"
                ;;

            stop|restart|status|open|logs|list|info|validate)
                "$SCRIPTS/maps.sh" "$@"
                ;;

            *)
                echo
                echo "Maps commands:"
                echo "  ./nomad maps start [state]"
                echo "  ./nomad maps stop"
                echo "  ./nomad maps restart"
                echo "  ./nomad maps status"
                echo "  ./nomad maps open"
                echo "  ./nomad maps logs"
                echo "  ./nomad maps list"
                echo "  ./nomad maps info state"
                echo "  ./nomad maps validate"
                echo
                ;;
        esac
        ;;

    dashboard)
        "$PYTHON" "$PROJECT_DIR/dashboard/server.py"
        ;;

    library)
        shift
        "$SCRIPTS/library.sh" "$@"
        ;;

    help|-h|--help)
        show_help
        ;;

    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;

esac
