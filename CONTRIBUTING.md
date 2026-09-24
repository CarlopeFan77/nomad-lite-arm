# Contributing to NOMAD Lite ARM

Thanks for your interest in contributing to NOMAD Lite ARM.

NOMAD Lite is an early-stage open-source project focused on building a lightweight offline knowledge and education platform for ARM64 Linux devices.

Contributions are welcome, especially from people testing the project on additional ARM64 hardware.

## Ways to Contribute

There are several useful ways to help:

* Report bugs
* Suggest features
* Improve documentation
* Test NOMAD Lite on additional ARM64 devices
* Report hardware and operating system compatibility
* Improve the dashboard
* Add or improve offline content integrations
* Improve installation and setup
* Submit code fixes or new features

Testing on Raspberry Pis, ARM64 single-board computers, Chromebooks, and other low-power ARM64 Linux devices is especially valuable.

## Before Contributing

NOMAD Lite is currently under active development.

Before beginning a major feature, consider opening a GitHub Issue first so the idea can be discussed before significant work is done.

Small bug fixes and documentation improvements generally do not require prior discussion.

## Development Environment

The primary development environment is currently:

* ARM64 / AArch64
* Debian 12
* Python 3
* Bash
* Kiwix
* Kolibri

Other ARM64 Linux environments may work but are not yet fully tested.

Clone the repository:

```bash
git clone https://github.com/CarlopeFan77/nomad-lite-arm.git
cd nomad-lite-arm
```

Check whether your system meets the current requirements:

```bash
./install.sh --check
```

Install the required dependencies:

```bash
./install.sh
```

## Making Changes

Create a new Git branch for your work instead of working directly on `main`.

For example:

```bash
git switch -c feature/my-feature
```

Make your changes and test them locally.

Before committing Bash changes, run:

```bash
bash -n nomad scripts/*.sh install.sh
```

Also test the relevant NOMAD Lite commands manually.

For example:

```bash
./nomad status
./nomad library list
./nomad education list
```

If your changes affect the dashboard, verify the affected functionality through the local dashboard as well.

## Code Guidelines

Please try to keep NOMAD Lite lightweight and understandable.

When contributing:

* Prefer simple solutions over unnecessary complexity
* Avoid adding dependencies unless they provide clear value
* Keep ARM64 and low-resource hardware in mind
* Avoid hard-coded user-specific paths
* Use project-relative paths whenever possible
* Preserve offline functionality where practical
* Keep large downloadable datasets out of the Git repository
* Add comments when behavior may not be obvious
* Update documentation when changing user-facing behavior

New features should not assume that users have large amounts of RAM or internal storage.

## Hardware Testing

If you test NOMAD Lite on hardware that has not previously been documented, please include as much of the following information as possible:

* Device name
* Processor
* Architecture
* RAM
* Operating system and version
* NOMAD Lite features tested
* Features that worked
* Features that failed
* Any special setup required

Hardware compatibility reports are useful even when no code changes are submitted.

## Bug Reports

When reporting a bug, please include:

* A clear description of the problem
* Steps to reproduce it
* What you expected to happen
* What actually happened
* Relevant terminal output or error messages
* Hardware and operating system information

You can collect basic system information with:

```bash
./nomad system
```

Please remove any private or sensitive information before posting logs or screenshots publicly.

## Pull Requests

Before opening a pull request:

1. Make sure your branch is up to date.
2. Test the affected functionality.
3. Check Bash scripts for syntax errors.
4. Keep unrelated changes out of the pull request.
5. Update documentation when necessary.
6. Write a clear description of what changed and why.

A pull request does not need to be perfect. Clear explanations and focused changes are more important than elaborate formatting.

## Dependencies

NOMAD Lite is intended for low-power systems, so new dependencies should be added carefully.

If a contribution requires a new dependency, please explain:

* Why it is needed
* What functionality it provides
* Whether a lighter alternative exists
* Whether it works on ARM64
* Whether it increases storage or memory requirements significantly

Dependencies required for installation should also be reflected in `install.sh`.

## Offline Content

Large offline content files such as ZIM archives, educational datasets, map data, or similar downloadable resources should generally not be committed directly to the repository.

NOMAD Lite should instead download or manage these resources separately so users can choose which content they want to store.

## License

By contributing to NOMAD Lite ARM, you agree that your contributions will be distributed under the project's Apache License 2.0.

## Questions and Ideas

For bugs, feature requests, compatibility reports, and project ideas, use GitHub Issues.

NOMAD Lite is still evolving, so feedback from people experimenting with ARM64 devices and offline computing is especially welcome.
