from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from hashlib import pbkdf2_hmac

import aiohttp

_LOGGER = logging.getLogger(__name__)

_INVALID_SID = "0000000000000000"


class FritzAuthError(Exception):
    pass


class FritzSession:
    """Fritz!Box Lua API session — handles login and log fetching."""

    def __init__(self, host: str, username: str, password: str, ssl: bool) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._sid: str | None = None
        self._base_url = f"{'https' if ssl else 'http'}://{host}"
        self._ssl = False if ssl else None  # skip cert verification for self-signed

    def _response_v1(self, challenge: str) -> str:
        raw = f"{challenge}-{self._password}".encode("utf-16le")
        return f"{challenge}-{hashlib.md5(raw).hexdigest()}"

    def _response_v2(self, challenge: str) -> str:
        _, iter1, salt1, iter2, salt2 = challenge.split("$")
        h1 = pbkdf2_hmac("sha256", self._password.encode(), bytes.fromhex(salt1), int(iter1))
        h2 = pbkdf2_hmac("sha256", h1, bytes.fromhex(salt2), int(iter2))
        return f"{salt2}${h2.hex()}"

    async def login(self, http: aiohttp.ClientSession) -> None:
        resp = await http.get(f"{self._base_url}/login_sid.lua?version=2", ssl=self._ssl)
        xml = ET.fromstring(await resp.text())

        sid = xml.findtext("SID", _INVALID_SID)
        if sid != _INVALID_SID:
            self._sid = sid
            return

        challenge = xml.findtext("Challenge", "")
        response = self._response_v2(challenge) if challenge.startswith("2$") else self._response_v1(challenge)

        data: dict[str, str] = {"response": response}
        if self._username:
            data["username"] = self._username

        resp = await http.post(f"{self._base_url}/login_sid.lua", data=data, ssl=self._ssl)
        xml = ET.fromstring(await resp.text())
        sid = xml.findtext("SID", _INVALID_SID)
        if sid == _INVALID_SID:
            raise FritzAuthError("Fritz!Box authentication failed — check username and password")
        self._sid = sid
        _LOGGER.debug("Fritz!Box login successful")

    async def fetch_logs(self, http: aiohttp.ClientSession) -> list[dict]:
        if not self._sid:
            await self.login(http)

        resp = await self._post_log(http)
        if resp.status == 403:
            _LOGGER.debug("Fritz!Box SID expired, re-authenticating")
            self._sid = None
            await self.login(http)
            resp = await self._post_log(http)

        raw = await resp.json(content_type=None)
        _LOGGER.debug("Raw Fritz!Box log response: %s", raw)
        entries = raw.get("data", {}).get("log", [])
        return [_parse_entry(e) for e in entries]

    async def _post_log(self, http: aiohttp.ClientSession) -> aiohttp.ClientResponse:
        return await http.post(
            f"{self._base_url}/data.lua",
            data={"sid": self._sid, "page": "log", "lang": "de", "filter": "all"},
            ssl=self._ssl,
        )


def _parse_entry(entry: list | dict) -> dict:
    if isinstance(entry, list):
        # Array format: [datetime_str, message, category_str, ...]
        return {
            "datetime": entry[0] if len(entry) > 0 else "",
            "message": entry[1] if len(entry) > 1 else "",
            "category": int(entry[2]) if len(entry) > 2 and entry[2] else 0,
        }
    return {
        "datetime": entry.get("date", "") or entry.get("datetime", ""),
        "message": entry.get("msg", "") or entry.get("message", ""),
        "category": int(entry.get("category", entry.get("group", 0)) or 0),
    }
