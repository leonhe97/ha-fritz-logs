# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Build a HACS-compatible custom integration for Home Assistant that fetches logs from a Fritz!Box router and exposes them as events or sensor entities, enabling automations based on Fritz!Box log entries (e.g., login attempts, device connections, firewall events).

## Approach: Standalone HACS Integration

This is a **standalone custom component** (not a fork of the official `fritz` integration). The official integration (`homeassistant/components/fritz/`) uses `fritzconnection` for TR-064 and the Fritz!Box HTTP API, but does not expose logs. We replicate the connection approach and add log fetching on top.

Key reason to avoid forking the core integration: HACS requires a standalone `custom_components/<domain>/` package — it cannot deliver patches to core. Forking means maintaining a divergent copy of the full `fritz` integration forever.

## Fritz!Box Log Fetching

Fritz!Box exposes logs via two mechanisms:
1. **TR-064 / SOAP** — `GetDeviceLog` action on the `DeviceInfo:1` service (via `fritzconnection`). Returns plain-text log lines.
2. **Lua HTTP endpoint** — `http://<fritz-ip>/query.lua?mq_log=logger:status/log` (requires session login via `sidlogin`). More structured but session-based.

Prefer TR-064 / `fritzconnection` for consistency with the official integration pattern.

## Key Libraries

- `fritzconnection` — already a dependency of the core `fritz` integration; handles TR-064 SOAP calls and auth. Import with `from fritzconnection.core.fritzconnection import FritzConnection`.
- `homeassistant` — standard HA framework; use `homeassistant.config_entries`, `homeassistant.helpers.entity`, `homeassistant.helpers.update_coordinator`.

## Custom Component Structure

```
custom_components/fritz_logs/
  __init__.py          # async_setup_entry / async_unload_entry
  config_flow.py       # ConfigFlow + OptionsFlow (host, port, username, password, poll_interval)
  coordinator.py       # DataUpdateCoordinator — fetches logs, deduplicates, fires events
  sensor.py            # Optional sensor entities (last log entry, log count)
  const.py             # DOMAIN, CONF_* constants, default poll interval
  manifest.json        # HACS manifest: domain, name, dependencies, requirements
  strings.json         # UI strings
  translations/en.json
hacs.json              # HACS metadata (name, render_readme, homeassistant min version)
```

## manifest.json Requirements

```json
{
  "domain": "fritz_logs",
  "name": "Fritz!Box Logs",
  "version": "0.1.0",
  "requirements": ["fritzconnection==1.14.0"],
  "dependencies": [],
  "codeowners": [],
  "iot_class": "local_polling"
}
```

## Development Setup

No build step — this is pure Python loaded directly by Home Assistant.

**Running locally with a real HA instance:**
```bash
# Copy the custom component into your HA config directory
cp -r custom_components/fritz_logs ~/.homeassistant/custom_components/

# Restart Home Assistant (if using the dev container approach):
# In VS Code with the HA devcontainer, press F5 or run the task "Run Home Assistant"
```

**Using the HA Core dev container (recommended):**
```bash
git clone https://github.com/home-assistant/core.git ha-core
cd ha-core
# Place custom_components/fritz_logs/ in ha-core/config/custom_components/
# Then: scripts/setup_dev_env and container start per HA contrib docs
```

**Linting / type checking:**
```bash
# From within HA core dev environment:
python -m pylint custom_components/fritz_logs
python -m mypy custom_components/fritz_logs
ruff check custom_components/fritz_logs
```

**Running HA integration tests (pytest-homeassistant-custom-component):**
```bash
pip install pytest-homeassistant-custom-component
pytest tests/
```

## Event Architecture

The coordinator fires HA events (`hass.bus.async_fire`) for each new log line, using a deduplicated set keyed on timestamp + message. Example event name: `fritz_logs_entry`. Downstream automations listen via `trigger: platform: event`.

Optionally, expose a `sensor` entity showing the last N log lines as attributes, but the primary value is the event bus approach since logs are ephemeral/streaming data, not state.

## HACS Compatibility Checklist

- `hacs.json` at repo root with `"name"` and `"render_readme": true`
- `custom_components/fritz_logs/manifest.json` with `version` field
- `custom_components/fritz_logs/strings.json` + `translations/en.json`
- GitHub repo must be public for HACS default store; use custom repo URL for private installs
- Minimum HA version declared in `hacs.json` as `"homeassistant": "2024.1.0"` (or later)
