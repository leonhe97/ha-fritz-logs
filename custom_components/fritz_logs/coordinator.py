from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fritzconnection.core.fritzconnection import FritzConnection
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_POLL_INTERVAL, CONF_SSL, DEFAULT_POLL_INTERVAL, DOMAIN, EVENT_LOG_ENTRY

_LOGGER = logging.getLogger(__name__)


def _parse_log_line(line: str) -> dict:
    parts = line.split(" ", 2)
    if len(parts) == 3:
        try:
            dt = datetime.strptime(f"{parts[0]} {parts[1]}", "%d.%m.%y %H:%M:%S")
            return {"message": parts[2], "timestamp": dt.isoformat(), "raw": line}
        except ValueError:
            pass
    return {"message": line, "timestamp": None, "raw": line}


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
        self._host: str = entry.data[CONF_HOST]
        self._username: str = entry.data[CONF_USERNAME]
        self._password: str = entry.data[CONF_PASSWORD]
        self._ssl: bool = entry.data.get(CONF_SSL, False)
        self._seen_lines: set[str] = set()
        self._initialized: bool = False

    async def _async_update_data(self) -> dict:
        try:
            raw: str = await self.hass.async_add_executor_job(self._fetch_log_text)
        except Exception as err:
            raise UpdateFailed(f"Fritz!Box log fetch failed: {err}") from err

        lines = [line.strip() for line in raw.splitlines() if line.strip()]

        if not self._initialized:
            self._seen_lines.update(lines)
            self._initialized = True
            return {"lines": lines}

        new_lines = [line for line in lines if line not in self._seen_lines]
        self._seen_lines.update(new_lines)

        # Log is newest-first; fire events oldest-first
        for line in reversed(new_lines):
            self.hass.bus.async_fire(EVENT_LOG_ENTRY, _parse_log_line(line))
            _LOGGER.debug("New Fritz!Box log entry: %s", line)

        return {"lines": lines}

    def _fetch_log_text(self) -> str:
        fc = FritzConnection(
            address=self._host,
            user=self._username,
            password=self._password,
            use_tls=self._ssl,
        )
        result = fc.call_action("DeviceInfo:1", "GetDeviceLog")
        return result.get("NewDeviceLog", "")
