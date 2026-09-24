#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="install"

if [[ "${1:-}" == "--check" ]]; then
    MODE="check"
elif [[ $# -gt 0 ]]; then
    echo "Usage: ./install.sh [--check]"
    exit 1
fi

info() {
    printf '[NOMAD] %s\n' "$1"
}

error() {
    printf '[ERROR] %s\n' "$1" >&2
}

check_system() {
    info "Checking system compatibility..."

    local arch
    arch="$(uname -m)"

    if [[ "$arch" != "aarch64" && "$arch" != "arm64" ]]; then
        error "Unsupported architecture: $arch"
        error "NOMAD Lite currently targets ARM64/AArch64 Linux systems."
        exit 1
    fi

    if [[ ! -r /etc/os-release ]]; then
        error "Could not identify this Linux distribution."
        exit 1
    fi

    source /etc/os-release

    if [[ "${ID:-}" != "debian" || "${VERSION_ID%%.*}" != "12" ]]; then
        error "Automatic installation currently supports Debian 12 only."
        error "Detected: ${PRETTY_NAME:-unknown Linux distribution}"
        exit 1
    fi

    info "Architecture: $arch"
    info "Operating system: ${PRETTY_NAME:-Debian 12}"
}

check_required_commands() {
    info "Checking NOMAD Lite dependencies..."

    local missing=0
    local cmd

    for cmd in bash python3 curl kiwix-serve kolibri; do
        if command -v "$cmd" >/dev/null 2>&1; then
            printf '  %-12s OK\n' "$cmd"
        else
            printf '  %-12s MISSING\n' "$cmd"
            missing=1
        fi
    done

    return "$missing"
}

install_core_packages() {
    info "Installing core packages..."

    sudo apt-get update

    sudo apt-get install -y \
        python3 \
        curl \
        ca-certificates \
        gnupg \
        dirmngr \
        kiwix-tools
}

install_kolibri() {
    if command -v kolibri >/dev/null 2>&1; then
        info "Kolibri is already installed."
        return
    fi

    info "Adding the Learning Equality Kolibri repository..."

    local key_id="DC5BAA93F9E4AE4F0411F97C74F88ADB3194DD81"
    local keyring="/usr/share/keyrings/learningequality-kolibri.gpg"
    local source_file="/etc/apt/sources.list.d/learningequality-ubuntu-kolibri.list"

    sudo gpg \
        --batch \
        --keyserver hkp://keyserver.ubuntu.com:80 \
        --recv-keys "$key_id"

    sudo gpg \
        --batch \
        --yes \
        --output "$keyring" \
        --export "$key_id"

    echo "deb [signed-by=$keyring] http://ppa.launchpad.net/learningequality/kolibri/ubuntu jammy main" \
        | sudo tee "$source_file" >/dev/null

    sudo apt-get update

    info "Installing Kolibri..."
    info "Kolibri may ask configuration questions during installation."

    sudo apt-get install kolibri
}

prepare_project() {
    info "Preparing NOMAD Lite files..."

    chmod +x "$PROJECT_DIR/nomad"

    if [[ -d "$PROJECT_DIR/scripts" ]]; then
        find "$PROJECT_DIR/scripts" \
            -maxdepth 1 \
            -type f \
            -name '*.sh' \
            -exec chmod +x {} +
    fi

    mkdir -p "$PROJECT_DIR/data/zim"
}

verify_installation() {
    info "Verifying installation..."

    local failed=0
    local cmd

    for cmd in bash python3 curl kiwix-serve kolibri; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            error "Missing command after installation: $cmd"
            failed=1
        fi
    done

    if ! bash -n "$PROJECT_DIR/nomad"; then
        error "Syntax check failed: nomad"
        failed=1
    fi

    if [[ -d "$PROJECT_DIR/scripts" ]]; then
        while IFS= read -r -d '' script; do
            if ! bash -n "$script"; then
                error "Syntax check failed: $script"
                failed=1
            fi
        done < <(
            find "$PROJECT_DIR/scripts" \
                -maxdepth 1 \
                -type f \
                -name '*.sh' \
                -print0
        )
    fi

    if [[ "$failed" -ne 0 ]]; then
        error "Installation verification failed."
        exit 1
    fi

    info "NOMAD Lite installation checks passed."
}

main() {
    printf '\n'
    printf 'NOMAD Lite ARM Installer\n'
    printf '========================\n'
    printf '\n'

    check_system

    if [[ "$MODE" == "check" ]]; then
        printf '\n'

        if check_required_commands; then
            info "All current dependencies are installed."
        else
            info "One or more dependencies are missing."
        fi

        printf '\n'
        printf 'Run ./install.sh to install missing dependencies.\n'
        exit 0
    fi

    if [[ "$EUID" -eq 0 ]]; then
        error "Run this installer as your normal user, not as root."
        error "The installer will request sudo when needed."
        exit 1
    fi

    if ! command -v sudo >/dev/null 2>&1; then
        error "sudo is required for automatic installation."
        exit 1
    fi

    sudo -v

    install_core_packages
    install_kolibri
    prepare_project
    verify_installation

    printf '\n'
    printf 'Installation complete.\n'
    printf 'Try: ./nomad status\n'
}

main "$@"
