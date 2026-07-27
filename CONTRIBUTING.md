# Contributing to Thermalright Trofeo LCD Screen App

Thanks for your interest in contributing! This is a Windows GUI application for controlling and customizing LCD displays on Thermalright CPU coolers and AIO pump heads.

## Development Setup

`ash
git clone https://github.com/overling/Thermalright-Trofeo-LCD-screen-app.git
cd Thermalright-Trofeo-LCD-screen-app
pip install -e '.[dev]'
`

## Running Tests and Linting

`ash
PYTHONPATH=src pytest tests/ -x -q   # run all tests
PYTHONPATH=src pytest tests/core/    # run domain layer tests only
PYTHONPATH=src pytest tests/services/  # run service layer tests only
PYTHONPATH=src pytest tests/adapters/  # run adapter layer tests only
ruff check .                         # lint
python -m pyright                    # type check
`

Tests are organized to mirror src/trcc/ hexagonal layers:
- 	ests/core/ — domain logic (pure unit tests)
- 	ests/services/ — application/use case layer
- 	ests/adapters/{device,infra,system}/ — infrastructure adapters
- 	ests/cli/, 	ests/api/, 	ests/gui/ — presentation adapters

All PRs must pass tests, uff check, and pyright with 0 errors.

## Building

`ash
python -m PyInstaller trcc-gui.spec --noconfirm
`

The built application will be in dist/trcc-gui/.

## Branch Strategy

1. Fork the repo and create a branch off main
2. Make your changes and ensure tests pass
3. Open a PR targeting main

## Ways to Contribute

- **Bug fixes** — Reproduce, write a test, fix it
- **Device support** — Add new Thermalright USB VID:PID mappings to src/trcc/core/registry.py
- **Hardware testing** — Own a Thermalright device? Help validate support
- **Documentation** — Install guides, troubleshooting tips, translations
