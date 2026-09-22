#!/bin/bash

case "$1" in

    start)
        echo "Starting Kolibri..."
        kolibri start

        echo
        echo "Kolibri started."
        echo "Open: http://localhost:8082"
        ;;

    stop)
        echo "Stopping Kolibri..."
        kolibri stop

        echo
        echo "Kolibri stopped."
        ;;

    status)
        output=$(kolibri status 2>&1 || true)

        if echo "$output" | grep -qiE "not running|stopped"; then
            echo "Kolibri is not running."

        elif echo "$output" | grep -qi "running"; then
            echo "Kolibri is running."
            echo "http://localhost:8082"

        else
            echo "$output"
        fi
        ;;

    *)
        echo "Usage:"
        echo "$0 start"
        echo "$0 stop"
        echo "$0 status"
        ;;

esac
