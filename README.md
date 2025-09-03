# kippy-homeassistant

A Home Assistant HACS integration for Kippy pet trackers.

Device trackers created by this integration are prefixed with `Kippy` and your pet's name (for example, `Kippy Tilly`).
If the Kippy service provides a profile picture for your pet, it will be shown on the device tracker.

## Installation

1. Copy `custom_components/kippy` to your Home Assistant `custom_components` directory or install via HACS.
2. Restart Home Assistant.
3. Configure the integration via the Home Assistant UI.

This repository is a work in progress and provides only a basic skeleton for future development.

## Testing

Run the test suite with:

```bash
pytest
```

The tests rely solely on Home Assistant's integration test utilities and do not require an internet connection.
