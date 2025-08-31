"""Constants for the Kippy integration."""
DOMAIN = "kippy"

# The integration exposes only device tracker entities. The list is kept
# separate so ``async_forward_entry_setups`` can be used in ``__init__``.
PLATFORMS: list[str] = ["device_tracker"]
