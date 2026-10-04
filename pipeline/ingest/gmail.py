"""Read-only Gmail access (auth + profile). Message fetching is added in Step 1.

Uses the machine-local OAuth client (credentials.json) and refresh token created by
tools/google-skill. Hard rules enforced here:
  - the granted scope must be exactly gmail.readonly — anything broader is refused
  - tokens are never printed, logged, or included in exception messages
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from ..config.settings import Settings

READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
API = "https://gmail.googleapis.com/gmail/v1/users/me"
REAUTH_HINT = "re-authenticate: cd tools/google-skill && npx tsx skills/gmail/scripts/gmail.ts auth"


class GmailAuthError(RuntimeError):
    pass


class GmailScopeError(GmailAuthError):
    pass


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
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self.s = settings
        self.session = session or requests.Session()
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
        if self._access_token is None:
            self.refresh()
        resp = self.session.get(f"{API}{path}", params=params, timeout=(10, 60),
                                headers={"Authorization": f"Bearer {self._access_token}"})
        if resp.status_code != 200:
            raise GmailAuthError(f"Gmail API {path}: HTTP {resp.status_code}")
        return resp.json()

    def profile(self) -> Profile:
        data = self._get("/profile")
        return Profile(email=data.get("emailAddress", "").lower(),
                       messages_total=int(data.get("messagesTotal", 0)), scopes=self._scopes)

    def check(self) -> tuple[bool, str]:
        """Doctor check: token refreshes, scope is read-only, account is the expected one."""
        try:
            p = self.profile()
        except GmailAuthError as e:
            return False, str(e)
        if p.email != self.s.gmail_account:
            return False, f"authenticated as {p.email}, expected {self.s.gmail_account}"
        return True, f"{p.email} | read-only scope | {p.messages_total:,} messages"
