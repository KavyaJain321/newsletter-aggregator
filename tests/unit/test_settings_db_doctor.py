from pathlib import Path

from pipeline.cli import _print, run_checks
from pipeline.config.settings import load_settings
from pipeline.llm.client import LLMClient, MockProvider
from pipeline.store.db import check_db, open_db


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


def test_dotenv_inline_comments(tmp_path):
    envfile = tmp_path / ".env"
    envfile.write_text('OLLAMA_MIN_FREE_VRAM_MB=9000      # refuse below this\n'
                       'OLLAMA_REMOTE_SSH=                # e.g. user@host\n'
                       'GROQ_MODEL="model#with-hash"      # quoted keeps #\n'
                       'OLLAMA_MODEL=qwen3:8b#tag-kept\n', encoding="utf-8")
    s = load_settings(env={}, dotenv_path=envfile)
    assert s.ollama_min_free_vram_mb == 9000
    assert s.ollama_remote_ssh is None
    assert s.groq_model == "model#with-hash"
    assert s.ollama_model == "qwen3:8b#tag-kept"   # '#' without preceding space is not a comment


def test_env_example_parses(tmp_path):
    """The shipped template must load cleanly when copied to .env."""
    from pipeline.config.settings import REPO_ROOT
    s = load_settings(env={}, dotenv_path=REPO_ROOT / "pipeline" / "env.example")
    assert s.ollama_min_free_vram_mb == 10000 and s.ollama_remote_ssh is None
    assert s.groq_api_key is None and s.ollama_base_url == "http://localhost:11434"


def test_relative_paths_resolve_to_repo(tmp_path):
    s = load_settings(env={"PIPELINE_DATA_DIR": "data"}, dotenv_path=tmp_path / "x")
    assert s.data_dir.is_absolute() and s.database_url is None


def test_database_url_is_never_shown(tmp_path):
    url = "postgresql://postgres.abcd:S3cr3t-pw@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
    s = load_settings(env={"DATABASE_URL": url}, dotenv_path=tmp_path / "x")
    assert s.database_url == url and "S3cr3t" not in repr(s) and "postgres.abcd:***@" in repr(s)


# --------------------------------------------------------------------- db
def test_db_check_leaves_no_trace(tmp_path):
    url = f"sqlite:///{(tmp_path / 'd' / 'p.db').as_posix()}"
    ok, detail = check_db(url)
    assert ok and "SQLite" in detail and "schema v0" in detail
    with open_db(url) as db:
        assert db.all("SELECT name FROM sqlite_master") == []


def test_db_check_failures(tmp_path):
    assert check_db(None) == (False, "DATABASE_URL is not set - add the Supabase session-pooler "
                                     "connection string to .env")
    blocker = tmp_path / "file"
    blocker.write_text("x")
    ok, _ = check_db(f"sqlite:///{(blocker / 'sub' / 'p.db').as_posix()}")  # parent is a file
    assert not ok
    ok, detail = check_db("mysql://u:pw@h/db")
    assert not ok and "unsupported" in detail and "pw" not in detail


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
