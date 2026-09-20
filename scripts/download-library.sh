#!/bin/bash

set -e

ZIM_DIR="$HOME/Projects/nomad-lite-arm/data/zim"

mkdir -p "$ZIM_DIR"

download() {
    NAME="$1"
    URL="$2"

    echo
    echo "================================="
    echo "Downloading: $NAME"
    echo "================================="

    curl -L -C - "$URL" \
        -o "$ZIM_DIR/$NAME"
}

case "$1" in

    general)
        download \
        "wikipedia_en_top_mini_2026-09.zim" \
        "https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_mini_2026-09.zim"
        ;;

    chemistry)
        download \
        "wikipedia_en_chemistry_maxi_2026-07.zim" \
        "https://download.kiwix.org/zim/wikipedia/wikipedia_en_chemistry_maxi_2026-07.zim"
        ;;

    astronomy)
        download \
        "wikipedia_en_astronomy_nopic_2026-08.zim" \
        "https://download.kiwix.org/zim/wikipedia/wikipedia_en_astronomy_nopic_2026-08.zim"
        ;;

    starter)
        "$0" general
        "$0" chemistry
        "$0" astronomy
        ;;

    *)
        echo "NOMAD Lite ARM Library Downloader"
        echo
        echo "Usage:"
        echo "  $0 general"
        echo "  $0 chemistry"
        echo "  $0 astronomy"
        echo "  $0 starter"
        ;;

esac
