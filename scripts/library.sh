#!/bin/bash

set -e

PROJECT_DIR="$HOME/Projects/nomad-lite-arm"
CATALOG="$PROJECT_DIR/config/library-catalog.txt"
ZIM_DIR="$PROJECT_DIR/data/zim"

mkdir -p "$ZIM_DIR"

get_entry() {
    grep "^$1|" "$CATALOG" || true
}

show_list() {
    echo
    echo "NOMAD Lite ARM Library"
    echo "=============================================================="
    printf "%-12s %-30s %-10s %-12s\n" \
        "ID" "COLLECTION" "SIZE" "STATUS"
    echo "--------------------------------------------------------------"

    while IFS='|' read -r id name size filename url; do

        [[ "$id" =~ ^#.*$ || -z "$id" ]] && continue

        if [ -f "$ZIM_DIR/$filename" ]; then
            status="Installed"
        else
            status="Available"
        fi

        printf "%-12s %-30s %-10s %-12s\n" \
            "$id" "$name" "$size" "$status"

    done < "$CATALOG"

    echo
}

show_installed() {
    echo
    echo "Installed NOMAD Lite collections"
    echo "================================"

    found=false

    while IFS='|' read -r id name size filename url; do

        [[ "$id" =~ ^#.*$ || -z "$id" ]] && continue

        if [ -f "$ZIM_DIR/$filename" ]; then
            echo "$id - $name ($size)"
            found=true
        fi

    done < "$CATALOG"

    if [ "$found" = false ]; then
        echo "No collections installed."
    fi

    echo
}

show_info() {
    entry=$(get_entry "$1")

    if [ -z "$entry" ]; then
        echo "Unknown collection: $1"
        exit 1
    fi

    IFS='|' read -r id name size filename url <<< "$entry"

    echo
    echo "$name"
    echo "================================"
    echo "ID:       $id"
    echo "Size:     $size"
    echo "File:     $filename"

    if [ -f "$ZIM_DIR/$filename" ]; then
        echo "Status:   Installed"
    else
        echo "Status:   Not installed"
    fi

    echo
}

install_collection() {
    entry=$(get_entry "$1")

    if [ -z "$entry" ]; then
        echo "Unknown collection: $1"
        echo
        echo "Run:"
        echo "  $0 list"
        exit 1
    fi

    IFS='|' read -r id name size filename url <<< "$entry"

    if [ -f "$ZIM_DIR/$filename" ]; then
        echo "$name is already installed."
        return
    fi

    echo
    echo "Installing $name"
    echo "Approximate size: $size"
    echo

    temp_file="$ZIM_DIR/$filename.part"

    curl -L -C - \
        "$url" \
        -o "$temp_file"

    mv "$temp_file" "$ZIM_DIR/$filename"

    echo
    echo "$name installed successfully."
}

remove_collection() {
    entry=$(get_entry "$1")

    if [ -z "$entry" ]; then
        echo "Unknown collection: $1"
        exit 1
    fi

    IFS='|' read -r id name size filename url <<< "$entry"

    if [ ! -f "$ZIM_DIR/$filename" ]; then
        echo "$name is not installed."
        return
    fi

    if [ "$2" = "--yes" ]; then
        answer="y"
    else
        echo "Remove $name?"
        read -r -p "[y/N]: " answer
    fi

    case "$answer" in
        y|Y|yes|YES)
            rm "$ZIM_DIR/$filename"
            echo "$name removed."
            ;;
        *)
            echo "Cancelled."
            ;;
    esac
}

install_starter() {
    install_collection general
    install_collection chemistry
    install_collection astronomy
}

case "$1" in

    list)
        show_list
        ;;

    installed)
        show_installed
        ;;

    info)
        if [ -z "$2" ]; then
            echo "Usage: $0 info COLLECTION"
            exit 1
        fi

        show_info "$2"
        ;;

    install)
        if [ -z "$2" ]; then
            echo "Usage: $0 install COLLECTION"
            exit 1
        fi

        install_collection "$2"
        ;;

    remove)
        if [ -z "$2" ]; then
            echo "Usage: $0 remove COLLECTION"
            exit 1
        fi

        remove_collection "$2" "$3"
        ;;

    starter)
        install_starter
        ;;

    *)
        echo
        echo "NOMAD Lite ARM Library Manager"
        echo
        echo "Commands:"
        echo "  $0 list"
        echo "  $0 installed"
        echo "  $0 info COLLECTION"
        echo "  $0 install COLLECTION"
        echo "  $0 remove COLLECTION"
        echo "  $0 starter"
        echo
        ;;

esac
