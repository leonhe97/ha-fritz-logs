DOMAIN = "fritz_logs"

CONF_SSL = "ssl"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_HOST = "192.168.178.1"
DEFAULT_USERNAME = ""
DEFAULT_SSL = False
DEFAULT_POLL_INTERVAL = 30

EVENT_LOG_ENTRY = f"{DOMAIN}_log_entry"

CONF_CATEGORIES = "categories"

# Best-guess mapping — actual values confirmed from debug logs
CATEGORY_NAMES: dict[int, str] = {
    1: "sys",
    2: "net",
    3: "fon",
    4: "wlan",
    5: "usb",
}

CATEGORY_LABELS: dict[str, str] = {
    "sys": "System",
    "net": "Internet",
    "fon": "Telephony",
    "wlan": "WiFi",
    "usb": "USB",
}

DEFAULT_CATEGORIES: list[str] = list(CATEGORY_LABELS)
