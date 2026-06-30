from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CATEGORY_NAMES,
    CONF_CATEGORIES,
    CONF_POLL_INTERVAL,
    CONF_SSL,
    DEFAULT_CATEGORIES,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    EVENT_LOG_ENTRY,
)
from .fritz_session import FritzAuthError, FritzSession

_LOGGER = logging.getLogger(__name__)


def _entry_key(entry: dict) -> str:
    return f"{entry.get('datetime', '')}|{entry.get('message', '')}"


class FritzLogsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        poll_interval = entry.options.get(
            CONF_POLL_INTERVAL, entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )
        self._fritz = FritzSession(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            ssl=entry.data.get(CONF_SSL, False),
        )
        self._selected: set[str] = set(
            entry.options.get(CONF_CATEGORIES, entry.data.get(CONF_CATEGORIES, DEFAULT_CATEGORIES))
        )
        self._seen_keys: set[str] = set()
        self._initialized: bool = False

    async def _async_update_data(self) -> dict:
        http = async_get_clientsession(self.hass)
        try:
            entries = await self._fritz.fetch_logs(http)
        except FritzAuthError as err:
            _LOGGER.error("Fritz!Box authentication failed: %s", err)
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            _LOGGER.error("Fritz!Box log fetch failed: %s", err)
            raise UpdateFailed(f"Fritz!Box log fetch failed: {err}") from err

        _LOGGER.debug("Fetched %d log entries", len(entries))

        if not self._initialized:
            self._seen_keys.update(_entry_key(e) for e in entries)
            self._initialized = True
            _LOGGER.info(
                "Fritz!Box Logs initialized — seeded %d existing entries, events start from next poll",
                len(entries),
            )
            return {"entries": entries}

        new_entries = [
            e for e in entries
            if _entry_key(e) not in self._seen_keys
            and CATEGORY_NAMES.get(e.get("category", 0), "unknown") in self._selected
        ]
        _LOGGER.debug("Poll complete: %d new of %d total entries", len(new_entries), len(entries))
        self._seen_keys.update(_entry_key(e) for e in new_entries)

        # data.lua returns newest-first; fire events oldest-first
        for entry in reversed(new_entries):
            category = entry.get("category", 0)
            payload = {
                "message": entry["message"],
                "datetime": entry.get("datetime", ""),
                "category": category,
                "category_name": CATEGORY_NAMES.get(category, "unknown"),
            }
            self.hass.bus.async_fire(EVENT_LOG_ENTRY, payload)
            _LOGGER.info(
                "fritz_logs_log_entry fired [%s]: %s",
                payload["category_name"],
                entry["message"],
            )

        return {"entries": entries}
