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
    echo "  maps start                Start offline Maps"
    echo "  maps stop                 Stop offline Maps"
    echo "  maps restart              Restart offline Maps"
    echo "  maps status               Show Maps status"
    echo "  maps open                 Open Maps in browser"
    echo "  maps logs                 Show recent Maps logs"
    echo "  maps list                 Show configured map states"
    echo "  maps info STATE           Show installed map packages"
    echo "  maps validate             Validate map configuration"
    echo
    echo "  system                    Show system information"
    echo "  dashboard                 Start web dashboard"
    echo
    echo "  library list              Show available content"
    echo "  library installed         Show installed content"
    echo "  library info NAME         Show collection information"
    echo "  library install NAME      Install a collection"
    echo "  library remove NAME       Remove a collection"
    echo
    echo "  help                      Show this help"
    echo
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

            start|stop|restart|status|open|logs|list|info|validate)
                "$SCRIPTS/maps.sh" "$@"
                ;;

            *)
                echo
                echo "Maps commands:"
                echo "  ./nomad maps start"
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
