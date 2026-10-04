"""Read-only Gmail access: auth, profile, message listing and raw fetch.

Uses the machine-local OAuth client (credentials.json) and refresh token created by
tools/google-skill. Hard rules enforced here:
  - the granted scope must be exactly gmail.readonly — anything broader is refused
  - tokens are never printed, logged, or included in exception messages
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterator

import requests

from ..config.settings import Settings

READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
API = "https://gmail.googleapis.com/gmail/v1/users/me"
REAUTH_HINT = "re-authenticate: cd tools/google-skill && npx tsx skills/gmail/scripts/gmail.ts auth"


class GmailAuthError(RuntimeError):
    pass


class GmailScopeError(GmailAuthError):
    pass


class GmailApiError(RuntimeError):
    """A Gmail API call failed after retries (never carries a token)."""


# Gmail signals per-user quota exhaustion with HTTP 403 (not only 429). Seen live 2026-10-04
# while backfilling ~180 messages back-to-back; the same ids succeeded moments later.
RATE_LIMIT_REASONS = {"rateLimitExceeded", "userRateLimitExceeded"}


def _error_reason(resp: Any) -> str:
    try:
        err = resp.json().get("error", {})
        errors = err.get("errors") or [{}]
        return str(errors[0].get("reason") or err.get("status") or "")
    except (ValueError, AttributeError, TypeError):
        return ""


@dataclass(frozen=True)
class RawMessage:
    id: str
    thread_id: str
    label_ids: tuple[str, ...]
    internal_date_ms: int        # when Gmail received it (UTC epoch ms)
    size_estimate: int
    raw: bytes                   # the full RFC 822 message, byte-exact


@dataclass(frozen=True)
class Profile:
    email: str
    messages_total: int
    scopes: tuple[str, ...]


def check_scopes(granted: str | list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Return the granted scopes if they are exactly gmail.readonly, else raise."""
    scopes = tuple(sorted(set(granted.split() if isinstance(granted, str) else granted)))
    if READONLY_SCOPE not in scopes:
        raise GmailScopeError(f"token lacks {READONLY_SCOPE}")
    extra = [s for s in scopes if s != READONLY_SCOPE]
    if extra:
        raise GmailScopeError(f"token has scopes beyond read-only: {extra} - refusing (hard rule)")
    return scopes


class GmailClient:
    def __init__(self, settings: Settings, session: requests.Session | None = None,
                 sleep: Callable[[float], None] = time.sleep, max_retries: int = 5):
        self.s = settings
        self.session = session or requests.Session()
        self.sleep, self.max_retries = sleep, max_retries
        self._access_token: str | None = None
        self._scopes: tuple[str, ...] = ()

    def _load_json(self, path, what: str) -> dict[str, Any]:
        if not path.is_file():
            raise GmailAuthError(f"{what} not found at {path} - {REAUTH_HINT}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise GmailAuthError(f"{what} at {path} is not valid JSON") from e

    def refresh(self) -> None:
        client_file = self._load_json(self.s.gmail_client_path, "OAuth client file")
        client = client_file.get("installed") or client_file.get("web")
        if not client or not client.get("client_id") or not client.get("client_secret"):
            raise GmailAuthError(f"OAuth client file {self.s.gmail_client_path} lacks client_id/client_secret")
        token = self._load_json(self.s.gmail_token_path, "Gmail token file")
        if not token.get("refresh_token"):
            raise GmailAuthError(f"no refresh_token in {self.s.gmail_token_path} - {REAUTH_HINT}")
        try:
            resp = self.session.post(
                client.get("token_uri", "https://oauth2.googleapis.com/token"),
                data={"client_id": client["client_id"], "client_secret": client["client_secret"],
                      "refresh_token": token["refresh_token"], "grant_type": "refresh_token"},
                timeout=(10, 30))
        except requests.RequestException as e:
            raise GmailAuthError(f"token endpoint unreachable ({e.__class__.__name__})") from None
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code != 200:
            err = body.get("error", f"HTTP {resp.status_code}")
            if err == "invalid_grant":
                raise GmailAuthError(f"refresh token expired or revoked (invalid_grant) - {REAUTH_HINT}")
            raise GmailAuthError(f"token refresh failed: {err}")
        self._scopes = check_scopes(body.get("scope") or token.get("scope", ""))
        self._access_token = body["access_token"]

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        """GET with retries: 429, rate-limit 403s, 5xx and network errors back off
        exponentially; a 401 triggers one token refresh."""
        if self._access_token is None:
            self.refresh()
        refreshed = False
        for attempt in range(self.max_retries + 1):
            backoff = min(2 ** (attempt + 1), 32)
            try:
                resp = self.session.get(f"{API}{path}", params=params, timeout=(10, 60),
                                        headers={"Authorization": f"Bearer {self._access_token}"})
            except requests.RequestException as e:
                if attempt == self.max_retries:
                    raise GmailApiError(f"Gmail API {path}: {e.__class__.__name__}") from None
                self.sleep(backoff)
                continue
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 401 and not refreshed:
                refreshed = True
                self.refresh()
                continue
            reason = _error_reason(resp)
            retryable = resp.status_code in (429, 500, 502, 503, 504) or (
                resp.status_code == 403 and reason in RATE_LIMIT_REASONS)
            if retryable and attempt < self.max_retries:
                self.sleep(backoff)
                continue
            raise GmailApiError(f"Gmail API {path}: HTTP {resp.status_code}" + (f" ({reason})" if reason else ""))
        raise GmailApiError(f"Gmail API {path}: retries exhausted")

    def list_ids(self, query: str, include_spam_trash: bool = True) -> Iterator[str]:
        """Every message id matching a Gmail search query (all pages). Spam/trash included
        by default so a newsletter misfiled as spam is still ingested (and reported)."""
        token: str | None = None
        while True:
            params: dict[str, Any] = {"q": query, "maxResults": 500,
                                      "includeSpamTrash": str(include_spam_trash).lower()}
            if token:
                params["pageToken"] = token
            page = self._get("/messages", **params)
            for m in page.get("messages", []):
                yield m["id"]
            token = page.get("nextPageToken")
            if not token:
                return

    def get_raw(self, msg_id: str) -> RawMessage:
        data = self._get(f"/messages/{msg_id}", format="raw")
        raw = data.get("raw")
        if not raw:
            raise GmailApiError(f"Gmail API message {msg_id}: no raw body returned")
        return RawMessage(id=data["id"], thread_id=data.get("threadId", ""),
                          label_ids=tuple(data.get("labelIds", [])),
                          internal_date_ms=int(data.get("internalDate", 0)),
                          size_estimate=int(data.get("sizeEstimate", 0)),
                          raw=base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))

    def profile(self) -> Profile:
        data = self._get("/profile")
        return Profile(email=data.get("emailAddress", "").lower(),
                       messages_total=int(data.get("messagesTotal", 0)), scopes=self._scopes)

    def check(self) -> tuple[bool, str]:
        """Doctor check: token refreshes, scope is read-only, account is the expected one."""
        try:
            p = self.profile()
        except (GmailAuthError, GmailApiError) as e:
            return False, str(e)
        if p.email != self.s.gmail_account:
            return False, f"authenticated as {p.email}, expected {self.s.gmail_account}"
        return True, f"{p.email} | read-only scope | {p.messages_total:,} messages"
