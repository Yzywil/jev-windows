import json

from jev_windows.cli import load_task, main
from jev_windows.contracts import JevError


def test_demo(capsys):
    assert main(["demo"]) == 0
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[-1]["status"] == "verified"
    assert events[-1]["mode"] == "offline_simulator"


def test_doctor_never_prints_key(monkeypatch, capsys):
    monkeypatch.setenv("TYPESAFE_API_KEY", "private-api-token")
    assert main(["doctor"]) == 0
    data = capsys.readouterr().out
    assert "private-api-token" not in data
    assert json.loads(data)["api_key_configured"] is True


def test_duplicate_json_rejected(tmp_path):
    import pytest

    p = tmp_path / "task.json"
    p.write_text('{"version":1,"version":2}')
    with pytest.raises(JevError, match="duplicate_json_key"):
        load_task(p)


def test_missing_task_is_clean_error(capsys):
    assert main(["run", "--task", "missing-task.json", "--window", "1"]) == 2
    assert json.loads(capsys.readouterr().out)["code"] == "local_file_or_configuration_error"
