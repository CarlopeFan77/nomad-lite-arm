#!/bin/bash

set -e

PROJECT_DIR="$HOME/Projects/nomad-lite-arm"

CATALOG="$PROJECT_DIR/config/education-catalog.txt"

STATE_DIR="$PROJECT_DIR/data/education"
INSTALLED_DIR="$STATE_DIR/installed"
INSTALLING_DIR="$STATE_DIR/installing"

CHANNEL_ID="c9d7f950ab6b5a1199e3d6c10d7f0103"
BASE_URL="https://studio.learningequality.org"

mkdir -p "$INSTALLED_DIR"
mkdir -p "$INSTALLING_DIR"


get_entry() {
    awk -F '|' -v id="$1" '
        $1 == id {
            print
            exit
        }
    ' "$CATALOG"
}


show_list() {
    echo
    echo "NOMAD Lite Education"
    echo "================================================================================"
    printf "%-20s %-15s %-24s %-12s\n" \
        "ID" "CATEGORY" "COURSE" "STATUS"

    echo "--------------------------------------------------------------------------------"

    while IFS='|' read -r id category name description node_id; do

        [[ "$id" =~ ^#.*$ || -z "$id" ]] && continue

        if [ -f "$INSTALLED_DIR/$id" ]; then
            status="Installed"
        else
            status="Available"
        fi

        printf "%-20s %-15s %-24s %-12s\n" \
            "$id" \
            "$category" \
            "$name" \
            "$status"

    done < "$CATALOG"

    echo
}


show_info() {
    entry=$(get_entry "$1")

    if [ -z "$entry" ]; then
        echo "Unknown course: $1"
        exit 1
    fi

    IFS='|' read -r id category name description node_id <<< "$entry"

    echo
    echo "$name"
    echo "================================"
    echo "ID:          $id"
    echo "Category:    $category"
    echo "Description: $description"
    echo "Source:      Khan Academy"

    if [ -f "$INSTALLED_DIR/$id" ]; then
        echo "Status:      Installed"
    else
        echo "Status:      Available"
    fi

    echo
}


install_course() {
    entry=$(get_entry "$1")

    if [ -z "$entry" ]; then
        echo "Unknown course: $1"
        echo
        echo "Run:"
        echo "  $0 list"
        exit 1
    fi

    IFS='|' read -r id category name description node_id <<< "$entry"

    if [ -f "$INSTALLED_DIR/$id" ]; then
        echo "$name is already installed."
        return
    fi

    echo
    echo "Installing $name"
    echo "Source: Khan Academy"
    echo

    installing_file="$INSTALLING_DIR/$id"

    touch "$installing_file"

    cleanup() {
        rm -f "$installing_file"
    }

    trap cleanup EXIT

    kolibri manage importcontent \
        --node_ids "$node_id" \
        network \
        "$CHANNEL_ID" \
        --baseurl "$BASE_URL"

    touch "$INSTALLED_DIR/$id"

    cleanup
    trap - EXIT

    echo
    echo "$name installed successfully."
}


case "$1" in

    list)
        show_list
        ;;

    info)
        if [ -z "$2" ]; then
            echo "Usage: $0 info COURSE"
            exit 1
        fi

        show_info "$2"
        ;;

    install)
        if [ -z "$2" ]; then
            echo "Usage: $0 install COURSE"
            exit 1
        fi

        install_course "$2"
        ;;

    *)
        echo
        echo "NOMAD Lite Education Manager"
        echo
        echo "Commands:"
        echo "  $0 list"
        echo "  $0 info COURSE"
        echo "  $0 install COURSE"
        echo
        ;;
esac
