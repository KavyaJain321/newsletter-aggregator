"""Gmail access — wraps the existing ~/.gmail-mcp/ OAuth into a reusable client.

Reuses the refresh token minted by the GongRzhe Gmail-MCP-Server (already
authenticated to notifyy1008@gmail.com). Read-only usage here.
"""
from __future__ import annotations
import base64
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from . import config

API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailError(RuntimeError):
    pass


def _access_token() -> str:
    """Refresh and return a live access token from the stored refresh token."""
    try:
        creds = json.loads(config.GMAIL_CREDS.read_text())
        keys = json.loads(config.GMAIL_OAUTH.read_text())["installed"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        raise GmailError(f"Gmail OAuth store missing/invalid at {config.GMAIL_DIR}: {e}")
    data = urllib.parse.urlencode({
        "client_id": keys["client_id"], "client_secret": keys["client_secret"],
        "refresh_token": creds["refresh_token"], "grant_type": "refresh_token",
    }).encode()
    try:
        resp = urllib.request.urlopen(urllib.request.Request(keys["token_uri"], data=data))
        return json.load(resp)["access_token"]
    except urllib.error.HTTPError as e:
        raise GmailError(f"token refresh failed ({e.code}) — re-auth may be needed: {e.read()[:200]}")


@dataclass
class GmailClient:
    token: str = field(default_factory=_access_token)

    # -- low-level ----------------------------------------------------------
    def _get(self, url: str) -> dict:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + self.token})
        for attempt in range(8):
            try:
                return json.load(urllib.request.urlopen(req))
            except urllib.error.HTTPError as e:
                if e.code in (403, 429, 500, 503):
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise GmailError(f"GET {url[:80]} -> {e.code}")
        raise GmailError(f"GET {url[:80]} -> gave up after retries")

    def whoami(self) -> dict:
        p = self._get(f"{API}/profile")
        return {"email": p.get("emailAddress"), "total": p.get("messagesTotal")}

    def search_ids(self, query: str) -> list[str]:
        ids, page = [], None
        while True:
            url = f"{API}/messages?maxResults=500&q=" + urllib.parse.quote(query)
            if page:
                url += "&pageToken=" + page
            r = self._get(url)
            ids += [m["id"] for m in r.get("messages", [])]
            page = r.get("nextPageToken")
            if not page:
                break
        return ids

    def get_raw(self, gmail_id: str) -> bytes:
        r = self._get(f"{API}/messages/{gmail_id}?format=raw")
        return base64.urlsafe_b64decode(r["raw"] + "==")

    def get_full(self, gmail_id: str) -> dict:
        return self._get(f"{API}/messages/{gmail_id}?format=full")

    def get_meta(self, gmail_id: str) -> dict:
        r = self._get(f"{API}/messages/{gmail_id}"
                      "?format=metadata&metadataHeaders=From&metadataHeaders=Date")
        hs = parse_headers(r["payload"])
        return {"from": hs.get("From", ""), "ts": int(r["internalDate"]) // 1000}

    # -- high-level ---------------------------------------------------------
    def segment_query(self, segment: str, window: str) -> str:
        seg = config.SEGMENTS[segment]
        clauses = [f"deliveredto:notifyy1008+{seg['tag']}@gmail.com"]
        for extra in config.PLAIN_SENDERS.get(segment, []):
            clauses.append(f"({extra})")
        joined = " OR ".join(clauses)
        return f"in:anywhere newer_than:{window} ({joined})"

    def list_segment(self, segment: str, window: str) -> list[str]:
        """Return gmail_ids for a segment within a window (e.g. '2d', '36h')."""
        return self.search_ids(self.segment_query(segment, window))


def parse_headers(payload: dict) -> dict:
    return {h["name"]: h["value"] for h in payload.get("headers", [])}


def sender_parts(from_header: str) -> tuple[str, str, str]:
    """Return (display_name, email, domain) from a From header."""
    m = re.search(r"<([^>]+)>", from_header)
    email = (m.group(1) if m else from_header).strip().lower()
    name = re.sub(r"\s*<[^>]+>", "", from_header).strip().strip('"')
    domain = email.split("@")[-1] if "@" in email else ""
    return name, email, domain
