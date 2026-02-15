# xten

Local-first media utility CLI for engineers.

Fast. Deterministic. Scriptable.

------------------------------------------------------------------------

## Features

-   Compress video by target size or CRF
-   Interactive guided compression mode
-   Fast lossless trimming
-   Media inspection (codec, resolution, duration)
-   Auto-increment output filenames (non-destructive by default)
-   `--force` overwrite support
-   `--dry-run` preview mode
-   Real-time progress bars

Linux-first in v0.1.0.

------------------------------------------------------------------------

## Installation

Recommended:

    pipx install xten-cli

Or with pip:

    pip install xten-cli

------------------------------------------------------------------------

## System Requirements

xten depends on:

-   Python 3.10+
-   ffmpeg (must be available in your PATH)

### Install ffmpeg (Linux)

Ubuntu / Debian:

    sudo apt install ffmpeg

Arch:

    sudo pacman -S ffmpeg

Fedora:

    sudo dnf install ffmpeg

Verify installation:

    ffmpeg -version

If ffmpeg is not available in PATH, xten will exit with an error.

xten does not bundle ffmpeg. It relies on your system installation to
remain lightweight and transparent.

------------------------------------------------------------------------

## Usage

### Compress

Interactive mode:

    xten compress video.mp4

Target size:

    xten compress video.mp4 --target 8mb

CRF quality mode:

    xten compress video.mp4 --crf 23

Overwrite existing output:

    xten compress video.mp4 --force

Dry run:

    xten compress video.mp4 --target 8mb --dry-run

------------------------------------------------------------------------

### Trim

Interactive trim:

    xten trim video.mp4

Explicit timestamps:

    xten trim video.mp4 --start 00:00:10 --end 00:00:25

Uses fast stream copy trimming by default.

------------------------------------------------------------------------

### Info

Inspect media:

    xten info video.mp4

Raw JSON output:

    xten info video.mp4 --json

------------------------------------------------------------------------

## Philosophy

xten is built around:

-   Local-first workflows
-   Non-destructive defaults
-   Predictable CLI behavior
-   Clean architecture
-   Minimal dependencies

No cloud. No telemetry. No hidden services.

------------------------------------------------------------------------

## Roadmap

-   Batch directory processing
-   Optional re-encode trim mode
-   Visual trimming workflow
-   JSON plan export
-   GPU acceleration support

------------------------------------------------------------------------

## License

MIT License

------------------------------------------------------------------------

Built by Jonathan Turner.