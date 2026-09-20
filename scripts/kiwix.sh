#!/bin/bash

PORT=8080
ZIM_DIR="$HOME/Projects/nomad-lite-arm/data/zim"
PID_FILE="$HOME/.kiwix-nomad.pid"
LOG_FILE="$HOME/.kiwix-nomad.log"

case "$1" in

    start)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Kiwix is already running."
            exit 0
        fi

        ZIM_FILES=("$ZIM_DIR"/*.zim)

        if [ ! -e "${ZIM_FILES[0]}" ]; then
            echo "No ZIM files found in:"
            echo "$ZIM_DIR"
            exit 1
        fi

        echo "Starting Kiwix..."

        kiwix-serve \
            -p "$PORT" \
            "${ZIM_FILES[@]}" \
            > "$LOG_FILE" 2>&1 &

        echo $! > "$PID_FILE"

        echo "Kiwix started."
        echo "Open: http://localhost:$PORT"
        ;;

    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "Kiwix does not appear to be running."
            exit 0
        fi

        PID=$(cat "$PID_FILE")

        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "Kiwix stopped."
        else
            echo "Kiwix was not running."
        fi

        rm -f "$PID_FILE"
        ;;

    status)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Kiwix is running."
            echo "http://localhost:$PORT"
        else
            echo "Kiwix is not running."
        fi
        ;;

    *)
        echo "Usage:"
        echo "$0 start"
        echo "$0 stop"
        echo "$0 status"
        ;;

esac
