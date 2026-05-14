from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_SECRET_ISOLATED_FILES = {Path("tests/test_agent_semantic_fallback.py")}


def _relative_test_path(request) -> Path:
    try:
        return Path(str(request.fspath)).resolve().relative_to(REPO_ROOT)
    except ValueError:
        return Path(str(request.fspath))


@pytest.fixture(autouse=True)
def isolate_report_provider_tests_from_local_ai_store(request, monkeypatch):
    # Profile-draft tests should never spend tokens or depend on a developer's
    # local AI key. Individual tests can delete this env var when they mock the
    # OpenAI-compatible client and want to exercise the request path directly.
    monkeypatch.setenv("TGCS_PROFILE_PATCH_DISABLE_LLM", "1")

    rel_path = _relative_test_path(request)
    is_report_package = len(rel_path.parts) >= 2 and rel_path.parts[:2] == ("tests", "report")
    if not is_report_package and rel_path not in REPORT_SECRET_ISOLATED_FILES:
        return

    from scripts import report_extraction

    # These tests usually model env-only or no-key provider states with
    # patch.dict(os.environ, clear=True). Keep the OS keyring out of that model
    # unless a test explicitly patches read_secret with fake stored credentials.
    monkeypatch.setattr(report_extraction.local_credentials, "read_secret", lambda target_name: None)
