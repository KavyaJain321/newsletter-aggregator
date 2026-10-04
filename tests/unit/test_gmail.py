import json

import pytest

from pipeline.ingest.gmail import (READONLY_SCOPE, GmailClient, GmailScopeError, check_scopes)
from tests.conftest import FakeResp, FakeSession

TOKEN_URI = "https://oauth2.googleapis.com/token"


def _write_creds(settings, scope=READONLY_SCOPE):
    settings.gmail_client_path.write_text(json.dumps({"installed": {
        "client_id": "cid", "client_secret": "csecret", "token_uri": TOKEN_URI}}), encoding="utf-8")
    settings.gmail_token_path.write_text(json.dumps({"refresh_token": "RT_SECRET", "scope": scope}), encoding="utf-8")


def test_check_scopes_readonly_only():
    assert check_scopes(READONLY_SCOPE) == (READONLY_SCOPE,)


@pytest.mark.parametrize("granted", [
    f"{READONLY_SCOPE} https://www.googleapis.com/auth/gmail.send",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.modify",
])
def test_check_scopes_refuses_broader(granted):
    with pytest.raises(GmailScopeError):
        check_scopes(granted)


def test_check_ok(settings):
    _write_creds(settings)
    sess = FakeSession().add("POST", "oauth2.googleapis.com/token",
                             FakeResp(200, {"access_token": "AT_SECRET", "scope": READONLY_SCOPE, "expires_in": 3599})) \
                        .add("GET", "/profile", FakeResp(200, {"emailAddress": "notifyy1008@gmail.com", "messagesTotal": 1234}))
    ok, detail = GmailClient(settings, session=sess).check()
    assert ok and "read-only" in detail and "1,234" in detail
    assert sess.calls[1]["headers"]["Authorization"] == "Bearer AT_SECRET"
    assert "SECRET" not in detail


def test_check_wrong_account(settings):
    _write_creds(settings)
    sess = FakeSession().add("POST", "token", FakeResp(200, {"access_token": "AT", "scope": READONLY_SCOPE})) \
                        .add("GET", "/profile", FakeResp(200, {"emailAddress": "someone@else.com"}))
    ok, detail = GmailClient(settings, session=sess).check()
    assert not ok and "expected notifyy1008@gmail.com" in detail


def test_check_invalid_grant_gives_reauth_hint(settings):
    _write_creds(settings)
    sess = FakeSession().add("POST", "token", FakeResp(400, {"error": "invalid_grant"}))
    ok, detail = GmailClient(settings, session=sess).check()
    assert not ok and "invalid_grant" in detail and "gmail.ts auth" in detail
    assert "RT_SECRET" not in detail


def test_check_refuses_broad_scope(settings):
    _write_creds(settings)
    sess = FakeSession().add("POST", "token", FakeResp(200, {
        "access_token": "AT", "scope": f"{READONLY_SCOPE} https://www.googleapis.com/auth/gmail.send"}))
    ok, detail = GmailClient(settings, session=sess).check()
    assert not ok and "beyond read-only" in detail


def test_check_missing_files(settings):
    ok, detail = GmailClient(settings, session=FakeSession()).check()
    assert not ok and "not found" in detail
