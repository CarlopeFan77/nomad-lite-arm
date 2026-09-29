#!/usr/bin/env bash

set -u


SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

ROOT_DIR="$(
    cd -- "$SCRIPT_DIR/.."
    pwd
)"


RUN_DIR="$ROOT_DIR/.run"

PID_FILE="$RUN_DIR/maps.pid"

LOG_FILE="$RUN_DIR/maps.log"


MAP_SERVER="$ROOT_DIR/scripts/serve_maps.py"

MAP_LIBRARY="$ROOT_DIR/scripts/map-library.py"

HOST="127.0.0.1"
PORT="8083"

MAP_URL="http://localhost:${PORT}/map"


# --------------------------------------------------
# Python selection
# --------------------------------------------------

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then

    PYTHON="$ROOT_DIR/.venv/bin/python"

else

    PYTHON="python3"

fi


# --------------------------------------------------
# Helpers
# --------------------------------------------------

ensure_run_dir() {

    mkdir -p "$RUN_DIR"
}


is_running() {

    if [[ ! -f "$PID_FILE" ]]; then
        return 1
    fi


    local pid

    pid="$(
        cat "$PID_FILE" 2>/dev/null
    )"


    if [[ -z "$pid" ]]; then
        return 1
    fi


    kill -0 "$pid" 2>/dev/null
}


cleanup_stale_pid() {

    if [[ -f "$PID_FILE" ]] \
        && ! is_running
    then

        rm -f "$PID_FILE"
    fi
}


start_maps() {

    ensure_run_dir

    cleanup_stale_pid


    if is_running; then

        echo "[NOMAD] Maps is already running."

        echo "[NOMAD] $MAP_URL"

        return 0
    fi


    if [[ ! -f "$MAP_SERVER" ]]; then

        echo "[NOMAD] Maps server not found:"
        echo "  $MAP_SERVER"

        return 1
    fi


    echo "[NOMAD] Starting Maps..."


    cd "$ROOT_DIR" || exit 1


    NOMAD_MAPS_HOST="$HOST" \
    NOMAD_MAPS_PORT="$PORT" \
    nohup "$PYTHON" "$MAP_SERVER" \
        >> "$LOG_FILE" \
        2>&1 &


    local pid=$!

    echo "$pid" > "$PID_FILE"


    sleep 1


    if is_running; then

        echo "[NOMAD] Maps started."
        echo "[NOMAD] $MAP_URL"

    else

        echo "[NOMAD] Maps failed to start."

        rm -f "$PID_FILE"

        echo
        echo "Recent log output:"
        echo "------------------"

        tail -n 20 "$LOG_FILE" \
            2>/dev/null || true

        return 1
    fi
}


stop_maps() {

    cleanup_stale_pid


    if ! is_running; then

        echo "[NOMAD] Maps is not running."

        return 0
    fi


    local pid

    pid="$(
        cat "$PID_FILE"
    )"


    echo "[NOMAD] Stopping Maps..."


    kill "$pid" 2>/dev/null || true


    for _ in {1..20}; do

        if ! kill -0 "$pid" 2>/dev/null; then
            break
        fi

        sleep 0.1
    done


    if kill -0 "$pid" 2>/dev/null; then

        echo "[NOMAD] Maps did not stop cleanly."

        return 1
    fi


    rm -f "$PID_FILE"


    echo "[NOMAD] Maps stopped."
}


status_maps() {

    cleanup_stale_pid


    if is_running; then

        local pid

        pid="$(
            cat "$PID_FILE"
        )"

        echo "[NOMAD] Maps: running"
        echo "[NOMAD] PID: $pid"
        echo "[NOMAD] URL: $MAP_URL"

    else

        echo "[NOMAD] Maps: stopped"
    fi
}


open_maps() {

    if ! is_running; then

        echo "[NOMAD] Maps is not running."
        echo "[NOMAD] Start it first with:"
        echo "  ./scripts/maps.sh start"

        return 1
    fi


    echo "[NOMAD] Opening:"
    echo "  $MAP_URL"


    if command -v xdg-open \
        >/dev/null 2>&1
    then

        xdg-open "$MAP_URL" \
            >/dev/null 2>&1 &

    fi
}


show_logs() {

    ensure_run_dir


    if [[ ! -f "$LOG_FILE" ]]; then

        echo "[NOMAD] No Maps log exists yet."

        return 0
    fi


    tail -n 50 "$LOG_FILE"
}


show_help() {

    cat <<EOF
NOMAD Maps

Usage:
  ./scripts/maps.sh start
  ./scripts/maps.sh stop
  ./scripts/maps.sh restart
  ./scripts/maps.sh status
  ./scripts/maps.sh open
  ./scripts/maps.sh list
  ./scripts/maps.sh info STATE
  ./scripts/maps.sh logs
  ./scripts/maps.sh validate
EOF
}


# --------------------------------------------------
# Command
# --------------------------------------------------

COMMAND="${1:-help}"


case "$COMMAND" in

    start)

        start_maps
        ;;


    stop)

        stop_maps
        ;;


    restart)

        stop_maps
        start_maps
        ;;


    status)

        status_maps
        ;;


    open)

        open_maps
        ;;


    logs)

        show_logs
        ;;

    list)

        "$PYTHON" \
            "$MAP_LIBRARY" \
            list
        ;;

    validate)

        "$PYTHON" \
            "$MAP_LIBRARY" \
            validate
        ;;


    info)

        if [[ $# -lt 2 ]]; then

            echo "Usage:"
            echo "  ./scripts/maps.sh info STATE"

            exit 1
        fi

        "$PYTHON" \
            "$MAP_LIBRARY" \
            info \
            "$2"
        ;;


    help|--help|-h)

        show_help
        ;;


    *)

        echo "Unknown Maps command:"
        echo "  $COMMAND"

        echo

        show_help

        exit 1
        ;;

esac
