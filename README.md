# NOMAD Lite ARM

**A lightweight offline knowledge and education environment for ARM64 Linux devices.**

NOMAD Lite ARM is a local-first toolkit designed to turn low-power ARM64 hardware into a portable offline information system.

The project combines offline reference libraries, educational content, lightweight local services, and a simple web dashboard into an environment intended for devices such as ARM64 single-board computers, low-cost laptops, Chromebooks, cyberdecks, and other resource-constrained Linux systems.

It is inspired by Project NOMAD by Crosstalk Solutions, but is an independent project focused specifically on lightweight ARM64 Linux hardware.

> **Project status:** Active development. The current build is being developed and tested on ARM64 Debian Linux. Additional ARM64 devices and distributions have not yet been fully tested.

## Why NOMAD Lite?

A useful offline knowledge system should not require powerful hardware.

NOMAD Lite is designed around a few principles:

* Run well on low-power ARM64 hardware
* Remain useful without an internet connection
* Keep storage requirements configurable
* Use lightweight and open-source software where practical
* Provide both reference material and structured educational content
* Allow large content libraries to live on removable or external storage
* Provide a simple interface instead of requiring users to manage every service manually

## Current Features

### Offline reference library

NOMAD Lite integrates with **Kiwix** to serve ZIM archives locally.

The library manager can:

* Display available offline collections
* Show installed collections
* Display collection information and storage requirements
* Download collections
* Resume interrupted downloads
* Remove installed collections

Content can include resources such as encyclopedias, science references, educational material, and other ZIM archives.

### Offline education

NOMAD Lite integrates with **Kolibri** for structured educational content.

The education system currently supports:

* Browsing available courses
* Viewing course information
* Installing individual courses
* Tracking installed content
* Displaying approximate download and storage requirements
* Starting and stopping the local Kolibri service

### Local dashboard

A lightweight local web dashboard provides a graphical interface for NOMAD Lite.

The dashboard can:

* View system information
* Start and stop Kiwix
* Start and stop Kolibri
* Browse the offline library
* Install and remove offline reference collections
* Browse available educational courses
* Start education downloads
* Display installation and download status

The dashboard runs locally and does not require an external web service.

### Command-line interface

Most NOMAD Lite functions can also be controlled through the main `nomad` command.

```text
./nomad start
./nomad stop
./nomad restart
./nomad status

./nomad kiwix start
./nomad kiwix stop
./nomad kiwix status

./nomad education start
./nomad education stop
./nomad education status

./nomad library list
./nomad library installed
./nomad library info NAME
./nomad library install NAME
./nomad library remove NAME

./nomad system
./nomad dashboard
```

## Current Test System

Development currently takes place on an **Acer Chromebook Spin 311** running the ChromeOS Linux Development Environment.

Current development hardware:

* MediaTek Kompanio 500
* ARM64 / AArch64
* 4 GB RAM
* 32 GB internal storage
* Debian 12
* ChromeOS Linux Development Environment

The intentionally modest hardware acts as a baseline for keeping the project lightweight.

## Requirements

NOMAD Lite currently targets an **ARM64/AArch64 Linux environment**.

Core software used by the project includes:

* Linux
* Bash
* Python 3
* Kiwix / `kiwix-serve`
* Kolibri
* `curl`
* Standard GNU/Linux command-line utilities

The local dashboard currently uses the Python standard library and does not require a separate set of third-party Python packages.

### Compatibility

The project is currently tested on Debian 12 ARM64.

Other ARM64 Linux systems—including ARM64 single-board computers and Raspberry Pi-class devices—are intended targets, but should be considered unverified until they have been tested.

32-bit ARM systems are not currently a supported target.

## Installation

Installation is currently intended for development and testing.

Some scripts still expect the project to exist at:

```text
~/Projects/nomad-lite-arm
```

Portable installation support and automated dependency setup are planned before the first stable release.

## Project Structure

```text
nomad-lite-arm/
├── config/       # Library and education catalogs
├── dashboard/    # Local web dashboard
├── data/         # Local content and application state
├── scripts/      # Service and library management scripts
├── nomad         # Main NOMAD Lite command
└── README.md
```

## Roadmap

Current development priorities include:

* Remove hard-coded installation paths
* Improve installation and first-time setup
* Expand the offline content catalog
* Improve download and storage reporting
* Test Raspberry Pi and other ARM64 Linux hardware
* Add support for external/removable storage
* Improve dashboard controls and status reporting
* Add additional lightweight offline tools
* Create packaged releases for easier installation

Longer-term, the goal is to make NOMAD Lite a simple platform for building portable offline knowledge systems on inexpensive ARM64 hardware.

## Use Cases

NOMAD Lite is being designed with several environments in mind:

* Raspberry Pi and ARM64 single-board computers
* Cyberdecks and portable computing builds
* Low-cost ARM laptops and Chromebooks
* Offline educational systems
* Portable reference libraries
* Emergency or disconnected information systems
* Homelabs and self-hosted experimentation

## Contributing

NOMAD Lite ARM is still early in development.

Testing on additional ARM64 Linux hardware, bug reports, compatibility results, feature suggestions, and contributions are welcome.

## Inspiration

NOMAD Lite ARM is inspired by **Project NOMAD by Crosstalk Solutions**.

This repository is an independent project and is not affiliated with or endorsed by Crosstalk Solutions.
