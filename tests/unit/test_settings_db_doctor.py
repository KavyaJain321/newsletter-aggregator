from pathlib import Path

from pipeline.cli import _print, run_checks
from pipeline.config.settings import load_settings
from pipeline.llm.client import LLMClient, MockProvider
from pipeline.store.db import check_writable, connect


# ---------------------------------------------------------------- settings
def test_defaults(tmp_path):
    s = load_settings(env={}, dotenv_path=tmp_path / "none.env")
    assert s.ollama_model == "qwen3:14b" and s.llm_provider_order == ("ollama", "groq")
    assert s.groq_api_key is None and s.llm_think is True
    assert s.gmail_account == "notifyy1008@gmail.com"


def test_dotenv_then_env_precedence(tmp_path):
    envfile = tmp_path / ".env"
    envfile.write_text('# c\nOLLAMA_MODEL="qwen3:8b"\nexport GROQ_MODEL=a\nLLM_THINK=false\n', encoding="utf-8")
    s = load_settings(env={"GROQ_MODEL": "b"}, dotenv_path=envfile)
    assert s.ollama_model == "qwen3:8b"       # from .env
    assert s.groq_model == "b"                # env wins over .env
    assert s.llm_think is False


def test_relative_paths_resolve_to_repo(tmp_path):
    s = load_settings(env={"PIPELINE_DATA_DIR": "data"}, dotenv_path=tmp_path / "x")
    assert s.data_dir.is_absolute() and s.db_path.name == "pipeline.db"


# --------------------------------------------------------------------- db
def test_db_writable_leaves_no_trace(tmp_path):
    db = tmp_path / "d" / "p.db"
    ok, detail = check_writable(db)
    assert ok and "SQLite" in detail
    tables = connect(db).execute("SELECT name FROM sqlite_master").fetchall()
    assert tables == []


def test_db_not_writable(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    ok, _ = check_writable(blocker / "sub" / "p.db")  # parent is a file
    assert not ok


# ----------------------------------------------------------------- doctor
class _Gmail:
    def __init__(self, ok): self.ok = ok
    def check(self): return (self.ok, "gmail detail")


def _by_name(checks):
    return {c.name: c for c in checks}


def test_doctor_all_green(settings, capsys):
    llm = LLMClient(settings, providers=[MockProvider(['{"ok": true}'])])
    checks = run_checks(settings, deep=True, gmail=_Gmail(True), llm=llm)
    c = _by_name(checks)
    assert c["config"].status == "OK"
    assert c["llm: at least one provider"].status == "OK"
    assert c["llm: live JSON round-trip"].status == "OK"
    assert c["database"].status == "OK"
    assert _print(checks) == 0
    assert "all required checks passed" in capsys.readouterr().out


def test_doctor_fails_without_gmail(settings):
    llm = LLMClient(settings, providers=[MockProvider([])])
    assert _print(run_checks(settings, gmail=_Gmail(False), llm=llm)) == 1


def test_doctor_fails_without_any_llm(settings):
    class Down(MockProvider):
        def health(self): return (False, "down")
    checks = run_checks(settings, gmail=_Gmail(True), llm=LLMClient(settings, providers=[Down()]))
    assert _by_name(checks)["llm: at least one provider"].status == "FAIL"
    assert _print(checks) == 1


def test_doctor_flags_unverified_sender(settings):
    checks = run_checks(settings, gmail=_Gmail(True), llm=LLMClient(settings, providers=[MockProvider()]))
    warn = _by_name(checks)["config: unverified senders"]
    assert warn.status == "WARN" and "axios_pro_rata" in warn.detail and not warn.required
