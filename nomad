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
    echo "  start                 Start NOMAD services"
    echo "  stop                  Stop NOMAD services"
    echo "  restart               Restart NOMAD services"
    echo "  status                Show service status"
    echo "  system                Show system information"
    echo "  dashboard             Start web dashboard"
    echo
    echo "  library list          Show available content"
    echo "  library installed     Show installed content"
    echo "  library info NAME     Show collection information"
    echo "  library install NAME  Install a collection"
    echo "  library remove NAME   Remove a collection"
    echo
    echo "  help                  Show this help"
    echo
}


case "${1:-help}" in

    start)
        "$SCRIPTS/kiwix.sh" start
        ;;

    stop)
        "$SCRIPTS/kiwix.sh" stop
        ;;

    restart)
        "$SCRIPTS/kiwix.sh" stop
        "$SCRIPTS/kiwix.sh" start
        ;;

    status)
        "$SCRIPTS/kiwix.sh" status
        ;;

    system)
        "$SCRIPTS/system-info.sh"
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
