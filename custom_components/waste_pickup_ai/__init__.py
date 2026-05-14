"""Waste Pickup AI custom integration."""

from __future__ import annotations

from typing import Any

from .compat import version_at_least
from .const import DOMAIN, MIN_HOME_ASSISTANT_VERSION, PLATFORMS


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Set up Waste Pickup AI from a config entry."""
    from homeassistant.const import __version__ as ha_version
    from homeassistant.exceptions import ConfigEntryError

    if not version_at_least(ha_version, MIN_HOME_ASSISTANT_VERSION):
        raise ConfigEntryError(
            f"Waste Pickup AI requires Home Assistant {MIN_HOME_ASSISTANT_VERSION} or newer; "
            f"current version is {ha_version}."
        )

    from .runtime import WastePickupRuntime, async_register_runtime_hass_bits

    await async_register_runtime_hass_bits(hass)
    runtime = WastePickupRuntime(hass, entry)
    await runtime.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if runtime:
            await runtime.async_unload()
    return unload_ok


async def _async_options_updated(hass: Any, entry: Any) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
