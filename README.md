# Fritz!Box Logs

A Home Assistant custom integration that polls your Fritz!Box router for log entries and fires them as HA events, enabling automations based on router activity.

## Features

- Polls Fritz!Box logs via TR-064 (no external cloud dependency)
- Fires a `fritz_logs_log_entry` event for every new log line
- Configurable poll interval (10–3600 seconds, default 30s)
- Only new entries since the last poll fire events — no flood on startup or restart
- Supports HTTP and HTTPS connections to the Fritz!Box

## Event payload

```yaml
event_type: fritz_logs_log_entry
data:
  message: "IPv6 prefix renewed successfully."
  timestamp: "2026-06-30T18:30:00"   # ISO 8601, null if unparseable
  raw: "30.06.26 18:30:00 IPv6 prefix renewed successfully."
```

## Automation example

```yaml
automation:
  - alias: "Alert on failed login to Fritz!Box"
    trigger:
      - platform: event
        event_type: fritz_logs_log_entry
        event_data:
          # partial match is not supported natively; use a template trigger instead
    condition:
      - condition: template
        value_template: "{{ 'login failed' in trigger.event.data.message | lower }}"
    action:
      - service: notify.mobile_app_phone
        data:
          message: "Fritz!Box login attempt: {{ trigger.event.data.message }}"
```

## Installation

### Via HACS (recommended)

1. In HA, open **HACS → Integrations**
2. Click the three-dot menu → **Custom repositories**
3. Add this repository URL, category: **Integration**
4. Find **Fritz!Box Logs** and install it
5. Restart Home Assistant

### Manual

Copy `custom_components/fritz_logs/` into your HA `config/custom_components/` directory and restart.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Fritz!Box Logs**
3. Enter your Fritz!Box IP (default `192.168.178.1`), username (often blank), and password
4. Optionally enable HTTPS and adjust the poll interval

## Credentials

The integration uses TR-064 (`DeviceInfo:1 / GetDeviceLog`). Use the same password you use to log into the Fritz!Box web UI. The username field can usually be left blank; enter `admin` if blank does not work.
