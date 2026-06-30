DOMAIN = "fritz_logs"

CONF_SSL = "ssl"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_HOST = "192.168.178.1"
DEFAULT_USERNAME = ""
DEFAULT_SSL = False
DEFAULT_POLL_INTERVAL = 30

EVENT_LOG_ENTRY = f"{DOMAIN}_log_entry"

CONF_CATEGORIES = "categories"

CATEGORY_LABELS: dict[str, str] = {
    "sys": "System",
    "net": "Internet",
    "fon": "Telephony",
    "wlan": "WiFi",
    "usb": "USB",
}

DEFAULT_CATEGORIES: list[str] = list(CATEGORY_LABELS)
