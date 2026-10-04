import json

import pytest

import base64

from pipeline.ingest.gmail import (READONLY_SCOPE, GmailApiError, GmailClient, GmailScopeError, check_scopes)
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


def _authed(settings, sess):
    _write_creds(settings)
    sess.routes.insert(0, ("POST", "oauth2.googleapis.com/token", __import__("collections").deque(
        [FakeResp(200, {"access_token": f"AT{i}", "scope": READONLY_SCOPE}) for i in range(3)])))
    return GmailClient(settings, session=sess, sleep=lambda _: None)


def test_list_ids_paginates_and_includes_spam(settings):
    sess = FakeSession().add("GET", "/messages", FakeResp(200, {"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "P2"}),
                             FakeResp(200, {"messages": [{"id": "c"}]}))
    g = _authed(settings, sess)
    assert list(g.list_ids("from:x@y.com")) == ["a", "b", "c"]
    gets = [c for c in sess.calls if c["method"] == "GET"]
    assert gets[0]["params"]["includeSpamTrash"] == "true" and gets[1]["params"]["pageToken"] == "P2"


def test_get_raw_decodes_unpadded_base64url(settings):
    raw = b"From: a@b.com\r\n\r\n\xf0\x9f\xa4\x96 body?>"
    enc = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sess = FakeSession().add("GET", "/messages/m1", FakeResp(200, {"id": "m1", "threadId": "t", "labelIds": ["INBOX"],
                                                                  "internalDate": "1790851158000", "raw": enc}))
    m = _authed(settings, sess).get_raw("m1")
    assert m.raw == raw and m.internal_date_ms == 1790851158000 and m.label_ids == ("INBOX",)
    assert sess.calls[-1]["params"]["format"] == "raw"


def test_retries_429_then_succeeds_and_refreshes_once_on_401(settings):
    sess = FakeSession().add("GET", "/profile", FakeResp(429, {}), FakeResp(401, {}),
                             FakeResp(200, {"emailAddress": "notifyy1008@gmail.com", "messagesTotal": 1}))
    g = _authed(settings, sess)
    assert g.profile().email == "notifyy1008@gmail.com"
    assert sum(1 for c in sess.calls if c["method"] == "POST") == 2      # initial + one refresh


def test_persistent_server_error_raises_without_token(settings):
    sess = FakeSession().add("GET", "/messages/m", *[FakeResp(503, {}) for _ in range(6)])
    g = _authed(settings, sess)
    with pytest.raises(GmailApiError, match="HTTP 503") as e:
        g.get_raw("m")
    assert "AT" not in str(e.value)


def _rate_limited():
    return FakeResp(403, {"error": {"code": 403, "errors": [{"reason": "userRateLimitExceeded"}]}})


def test_rate_limit_403_is_retried_with_backoff(settings):
    sleeps = []
    sess = FakeSession().add("GET", "/messages/m", _rate_limited(), _rate_limited(),
                             FakeResp(200, {"id": "m", "raw": "QQ"}))
    _write_creds(settings)
    sess.routes.insert(0, ("POST", "token", __import__("collections").deque(
        [FakeResp(200, {"access_token": "AT", "scope": READONLY_SCOPE})])))
    g = GmailClient(settings, session=sess, sleep=sleeps.append)
    assert g.get_raw("m").raw == b"A" and sleeps == [2, 4]


def test_permission_403_is_not_retried(settings):
    sess = FakeSession().add("GET", "/messages/m", FakeResp(403, {"error": {"errors": [{"reason": "insufficientPermissions"}]}}))
    g = _authed(settings, sess)
    with pytest.raises(GmailApiError, match=r"HTTP 403 \(insufficientPermissions\)"):
        g.get_raw("m")
    assert sum(1 for c in sess.calls if c["method"] == "GET") == 1
