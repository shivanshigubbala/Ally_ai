import importlib


def test_reports_directory_is_resolved_from_repo_root():
    module = importlib.import_module("backend.general_physician.agent")

    assert module.REPORTS_DIR.name == "reports"
    assert module.REPORTS_DIR.exists() or module.REPORTS_DIR.parent.exists()
