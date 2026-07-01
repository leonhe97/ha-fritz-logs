# Fritz!Box Logs

A Home Assistant custom integration that polls your Fritz!Box router for log entries and fires them as HA events, enabling automations based on router activity.

## Features

- Polls all Fritz!Box log categories (sys, net, fon, wlan, usb) via the Lua API
- Fires a `fritz_logs_log_entry` event for every new log entry
- Configurable poll interval (10–3600 seconds, default 30s) and per-category filter
- Only new entries since the last poll fire events — no flood on startup or restart

## Event payload

```yaml
event_type: fritz_logs_log_entry
data:
  message: "Internetverbindung wurde erfolgreich hergestellt."
  datetime: "01.07.26 08:15:00"
  category: "net"   # one of: sys, net, fon, wlan, usb
```

## Testing

In **Developer Tools → Events**, subscribe to `fritz_logs_log_entry` and click **Start listening** before the next poll cycle. Any new Fritz!Box log entry will appear here in real time.

## Automation examples

### Alert on failed login

```yaml
automation:
  - alias: "Fritz!Box: alert on failed login"
    trigger:
      - platform: event
        event_type: fritz_logs_log_entry
    condition:
      - condition: template
        value_template: >
          {{ 'anmeldung' in trigger.event.data.message | lower and
             trigger.event.data.category == 'sys' }}
    action:
      - service: notify.mobile_app_phone
        data:
          message: "Fritz!Box login: {{ trigger.event.data.message }}"
```

### Cable internet — DS-Lite / AFTR error reconnect

On DS-Lite connections (common with German cable ISPs), the Fritz!Box occasionally
fails to resolve the AFTR tunnel endpoint and loses IPv4 connectivity. This automation
triggers a reconnect automatically with a 1-hour cooldown to prevent reconnect loops.

Requires the [Fritz!Box Tools](https://www.home-assistant.io/integrations/fritz/) integration.

```yaml
automation:
  - alias: "Fritz!Box: reconnect on DS-Lite AFTR failure"
    mode: single
    trigger:
      - platform: event
        event_type: fritz_logs_log_entry
    condition:
      - condition: template
        value_template: >
          {{ trigger.event.data.message | regex_search('AFTR .* kann nicht aufgelöst werden') }}
      - condition: template
        value_template: >
          {{ (now() - state_attr('automation.fritz_box_reconnect_on_ds_lite_aftr_failure', 'last_triggered')).total_seconds() > 3600
             if state_attr('automation.fritz_box_reconnect_on_ds_lite_aftr_failure', 'last_triggered') else true }}
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Fritz!Box: AFTR failure detected"
          message: "Triggering reconnect — {{ trigger.event.data.datetime }}"
      - service: fritz.reconnect
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
4. Optionally adjust the poll interval and select which log categories to monitor

## No entities

This integration creates no entities. It works purely by firing events on the HA event bus — nothing will appear in your devices or entities list after setup. Use **Developer Tools → Events** to verify it's working (see Testing above).

## Credentials

The integration authenticates via the Fritz!Box Lua API (the same session mechanism the web UI uses). Use your admin password or a dedicated Fritz!Box service account (recommended). The username field can be left blank for the default admin account.
