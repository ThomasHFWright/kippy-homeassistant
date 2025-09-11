# Kippy for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-1f6feb.svg)](https://hacs.xyz)
[![license](https://img.shields.io/github/license/ThomasHFWright/kippy-homeassistant-hacs)](LICENSE)

Integrate [Kippy](https://www.kippy.eu/) pet trackers with Home Assistant. Track your pet's location, monitor activity and battery levels, and control tracker features directly from your smart home dashboard.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [HACS (recommended)](#hacs-recommended)
  - [Manual](#manual)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- Device tracker for each registered pet with profile picture
- Sensors for activity, battery, and more
- Buttons, numbers and switches for supported tracker actions
- Configurable activity update interval
- Automatic configuration through Home Assistant's UI

## Installation

### HACS (recommended)

1. In HACS, add this repository as a **Custom Repository**.
2. Install the **Kippy** integration.
3. Restart Home Assistant to load the integration.

### Manual

1. Download the latest release and copy `custom_components/kippy` into your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.

## Configuration

1. Navigate to _Settings → Devices & Services_.
2. Click **Add Integration** and search for **Kippy**.
3. Sign in with your Kippy account and select your tracker.
4. Adjust the activity update interval (default 15 minutes) from the integration options if desired.

The integration will create a device tracker and associated sensors for each pet.

## Troubleshooting

If the integration fails to load or entities are missing:

- Confirm your Kippy subscription is active.
- Enable debug logging to gather more information:

  ```yaml
  logger:
    logs:
      custom_components.kippy: debug
  ```

## Contributing

Contributions are welcome! Please run `pre-commit run --files README.md` and the test suite before submitting a pull request.

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE) for details.
