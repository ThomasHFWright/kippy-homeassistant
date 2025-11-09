# Kippy for Home Assistant

[![GitHub Repo stars][stars-shield]][stars]
[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![Community Forum][community-shield]][community]
[![hacs][hacsbadge]][hacs]
[![GitHub Activity][commits-shield]][commits]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeACoffee][bmc-shield]][bmc]

Integrate [Kippy](https://www.kippy.eu/) pet trackers with Home Assistant. Track your pet's location, monitor activity and battery levels, and control tracker features directly from your smart home dashboard.

This integration has been built to support Kippy Cat. It'll probably work with Kippy Evo and Kippy Dog, though I don't have either of these to test with. I'd appreciate some others testing to work out the kinks.

## Features

1. Creates a device tracker per Kippy in your account.
2. Retrieve location updates with different rates for idle/live tracking.
3. Enable/disable live tracking
4. Enable/disable energy saving mode
5. Fetch activity stats

## Installation

### Manually

Get the folder `custom_components/kippy` in your HA `config/custom_components`

### Via [HACS](https://hacs.xyz/)

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=ThomasHFWright&repository=kippy-homeassistant&category=integration" target="_blank"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

## Configuration

1. <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=kippy" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Open your Home Assistant instance and start setting up a new integration." /></a>
2. Sign in with your Kippy credentials and choose the trackers to import.

## Usage

Check out the [wiki](https://github.com/ThomasHFWright/kippy-homeassistant/wiki) for what all the settings mean and all available returned data.

## Contributions are welcome!

Contributions are welcome! Please open an issue or pull request with improvements.

In particular I could use some help trying to load historical activity data. The activity data only refreshes on Kippy's server as and when the Kippy tracker runs its location update schedule, ranging from every 1hr to every 24 hours. The Activity API can return previous days' data, but I can't figure a way to store it, so activity data only stores the current day's data up to the time the most recent GPS update timer runs.

Running `python script/hassfest --integration-path custom_components/kippy` and `pytest ./tests --cov=custom_components.kippy --cov-report term-missing` locally before submitting helps keep the project healthy.

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/ThomasHFWright/kippy-homeassistant.svg
[commits]: https://github.com/ThomasHFWright/kippy-homeassistant/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[license-shield]: https://img.shields.io/github/license/ThomasHFWright/kippy-homeassistant.svg
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40ThomasHFWright-blue.svg
[releases-shield]: https://img.shields.io/github/v/release/ThomasHFWright/kippy-homeassistant.svg
[community-shield]: https://img.shields.io/badge/community-forum-blue.svg
[community]: https://community.home-assistant.io/t/kippy-pet-gps-tracker-custom-integration/933073
[releases]: https://github.com/ThomasHFWright/kippy-homeassistant/releases
[user_profile]: https://github.com/ThomasHFWright
[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[stars-shield]: https://img.shields.io/github/stars/ThomasHFWright/kippy-homeassistant.svg
[stars]: https://github.com/ThomasHFWright/kippy-homeassistant/stargazers
[bmc-shield]: https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg?logo=buy-me-a-coffee
[bmc]: https://buymeacoffee.com/thomashfwright
