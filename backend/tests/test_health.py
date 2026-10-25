def test_health_returns_ok(client) -> None:
    """GET /health 는 200 과 {"status":"ok"} 를 돌려준다."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_documents_list_returns_rows(client) -> None:
    r = client.get("/api/v1/documents")
    assert r.status_code == 200
    문서들 = r.json()
    assert len(문서들) > 0
    assert 문서들[0]["security_level"] in ("일반", "3급", "대외비")
    # secret_note 는 응답 모델에 없으므로 밖으로 나가면 안 된다.
    assert "secret_note" not in 문서들[0]


def test_unknown_document_returns_404_with_code(client) -> None:
    r = client.get("/api/v1/documents/DOC-HR-999")
    assert r.status_code == 404
    본문 = r.json()
    assert 본문["code"] == "not_found"
    assert "DOC-HR-999" in 본문["message"]