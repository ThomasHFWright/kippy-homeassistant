# Kippy for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

Integrate [Kippy](https://www.kippy.eu/) pet trackers with Home Assistant. Track your pet's location, monitor activity and battery levels, and control tracker features directly from your smart home dashboard.

This integration has been built to support Kippy Cat. It'll probably work with Kippy Evo and Kippy Dog, though I don't have either of these to test with. I'd appreciate some others testing to work out the kinks.

## Features

1. Creates a device tracker per Kippy in your account.
2. Retrieve location updates as per
3. Enable/disable live tracking
4. Enable/disable energy saving mode
5. Fetch activity stats

## Installation

### Manually

Get the folder `custom_components/petlibro` in your HA `config/custom_components`

### Via [HACS](https://hacs.xyz/)

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=ThomasHFWright&repository=kippy-homeassistant-hacs&category=integration" target="_blank"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

## Configuration

1. <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=kippy" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Open your Home Assistant instance and start setting up a new integration." /></a>
2. Sign in with your Kippy credentials and choose the trackers to import.

## Usage

Check out the wiki for what all the settings mean and all available returned data.

## Contributions are welcome!

Contributions are welcome! Please open an issue or pull request with improvements.

In particular I could use some help trying to load historical activity data. The activity data only refreshes on Kippy's server as and when the Kippy tracker runs its location update schedule, ranging from every 1hr to every 24 hours. The Activity API can return previous days' data, but I can't figure a way to store it, so activity data only stores the current day's data up to the time the most recent GPS update timer runs.

Running `python script/hassfest --integration-path custom_components/kippy` and `pytest ./tests --cov=custom_components.kippy --cov-report term-missing` locally before submitting helps keep the project healthy.

## Credits

Many design patterns were inspired by [integration_blueprint].

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
