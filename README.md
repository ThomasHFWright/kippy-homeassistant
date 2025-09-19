# Kippy for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

Integrate [Kippy](https://www.kippy.eu/) pet trackers with Home Assistant. Track your pet's location, monitor activity and battery levels, and control tracker features directly from your smart home dashboard.

**This integration will set up the following platforms.**

| Platform          | Description                                                  |
| ----------------- | ------------------------------------------------------------ |
| `binary_sensor`   | Reports tracker health information such as geofence status.  |
| `button`          | Provides tracker actions like pinging the device.            |
| `device_tracker`  | Exposes each pet's latest known location and status.         |
| `number`          | Configures supported numeric settings (for example, refresh intervals). |
| `sensor`          | Surfaces activity, battery and other telemetry readings.     |
| `switch`          | Toggles available tracker features.                          |

## Installation

1. Using the tool of choice, open the directory for your Home Assistant configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory, create it.
3. Inside `custom_components`, create a new directory called `kippy`.
4. Download all of the files from the `custom_components/kippy/` directory in this repository.
5. Copy the files you downloaded into the `custom_components/kippy/` directory you just created.
6. Restart Home Assistant.
7. In the Home Assistant UI, go to **Settings → Devices & Services**, click **Add Integration**, and search for **Kippy**.

Using your Home Assistant configuration directory as a starting point, you should now also have this structure:

```text
custom_components/kippy/__init__.py
custom_components/kippy/api.py
custom_components/kippy/binary_sensor.py
custom_components/kippy/button.py
custom_components/kippy/config_flow.py
custom_components/kippy/const.py
custom_components/kippy/coordinator.py
custom_components/kippy/device_tracker.py
custom_components/kippy/helpers.py
custom_components/kippy/manifest.json
custom_components/kippy/number.py
custom_components/kippy/quality_scale.yaml
custom_components/kippy/sensor.py
custom_components/kippy/strings.json
custom_components/kippy/switch.py
custom_components/kippy/translations/en.json
```

## Configuration is done in the UI

1. Navigate to **Settings → Devices & Services**.
2. Select **Add Integration** and search for **Kippy**.
3. Sign in with your Kippy credentials and choose the trackers to import.
4. Adjust the integration options (such as the activity refresh interval) as needed after setup.

## Contributions are welcome!

Contributions are welcome! Please open an issue or pull request with improvements. Running `python script/hassfest --integration-path custom_components/kippy` and `pytest ./tests --cov=custom_components.kippy --cov-report term-missing` locally before submitting helps keep the project healthy.

## Credits

This project started from the Home Assistant custom component cookiecutter by [@oncleben31](https://github.com/oncleben31). Many design patterns were inspired by [integration_blueprint].

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/ThomasHFWright/kippy-homeassistant-hacs.svg?style=for-the-badge
[commits]: https://github.com/ThomasHFWright/kippy-homeassistant-hacs/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/ThomasHFWright/kippy-homeassistant-hacs.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40ThomasHFWright-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/v/release/ThomasHFWright/kippy-homeassistant-hacs.svg?style=for-the-badge
[releases]: https://github.com/ThomasHFWright/kippy-homeassistant-hacs/releases
[user_profile]: https://github.com/ThomasHFWright
[integration_blueprint]: https://github.com/custom-components/integration_blueprint
