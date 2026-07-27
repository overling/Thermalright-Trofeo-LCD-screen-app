# Thermalright Trofeo LCD Screen App

A Windows GUI application for controlling and customizing LCD displays on Thermalright CPU coolers and AIO pump heads.

## Features

- **LCD Display Control** — Customize LCD screens on supported Thermalright devices
- **Theme Management** — Browse, apply, import, and export local and cloud themes
- **Slideshow Mode** — Auto-rotate through selected themes with configurable interval
- **LED Control** — Customize LED segment displays
- **System Info** — Real-time sensor monitoring (CPU, GPU, temperatures, fan speeds)
- **Multi-language Support** — English, Chinese, German, Russian, French, and more

## Supported Devices

- Thermalright 11.3" Trofeo LCD
- And other Thermalright LCD/LED devices (see device list in app)

## Installation

### From Release

Download the latest release from the [Releases page](https://github.com/overling/Thermalright-Trofeo-LCD-screen-app/releases), extract, and run 	rcc-gui.exe.

### From Source

`
git clone https://github.com/overling/Thermalright-Trofeo-LCD-screen-app.git
cd Thermalright-Trofeo-LCD-screen-app
pip install -e .
python -m trcc
`

### Build with PyInstaller

`
python -m PyInstaller trcc-gui.spec --noconfirm
`

The built application will be in dist/trcc-gui/.

## Usage

Run 	rcc-gui.exe to launch the GUI. Use the tabs to browse themes, adjust LCD settings, configure LED displays, and monitor system sensors.

## Requirements

- Windows 10/11
- Python 3.11+ (for building from source)
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (bundled for sensor monitoring)

## License

This project is provided as-is for the Thermalright community.
