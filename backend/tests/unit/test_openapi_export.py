import json
from pathlib import Path

from salary_api.openapi import main


def test_export_writes_the_openapi_document_as_stable_json(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"

    exit_code = main([str(target)])

    text = target.read_text(encoding="utf-8")
    document = json.loads(text)
    assert exit_code == 0
    assert "/api/v1/health" in document["paths"]
    assert text == json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
