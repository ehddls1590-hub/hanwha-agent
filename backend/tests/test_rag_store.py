from types import SimpleNamespace

from app.rag.store import _row


def test_row_includes_document_version() -> None:
    chunk = SimpleNamespace(
        id=1,
        locator="제14조(숙박비)",
        kind="조항",
        text="숙박비 내용",
    )
    version = SimpleNamespace(version="v2.0", status="현행")
    document = SimpleNamespace(
        id="DOC-HR-014",
        title="국내출장 여비 규정",
        dept_id="HR",
        security_level="일반",
    )

    result = _row(chunk, version, document, 0.9)

    assert result["version"] == "v2.0"
    assert result["version_status"] == "현행"
