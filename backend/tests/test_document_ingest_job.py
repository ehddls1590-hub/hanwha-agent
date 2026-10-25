from contextlib import nullcontext
from types import SimpleNamespace

from app.rag import chunker, embedder, parser, store
from app.services import document_service


def test_save_chunks_replaces_existing_chunks() -> None:
    old_chunk = object()
    version = SimpleNamespace(
        chunks=[old_chunk],
        id=7,
        doc_id="DOC-FI-009",
        version="v2.4",
        chunk_count=0,
    )
    draft = SimpleNamespace(kind="조항", locator="p.1", text="본문")

    class FakeSession:
        def __init__(self) -> None:
            self.deleted: list[object] = []
            self.added: list[object] = []

        def delete(self, item: object) -> None:
            self.deleted.append(item)

        def add(self, item: object) -> None:
            self.added.append(item)

        def flush(self) -> None:
            pass

    session = FakeSession()

    count = store.save_chunks(session, version, [draft], [[0.1, 0.2]])

    assert count == 1
    assert session.deleted == [old_chunk]
    assert len(session.added) == 1
    assert version.chunk_count == 1


def test_ingest_document_records_model_label(monkeypatch) -> None:
    version = SimpleNamespace(version="v2.4")
    document = SimpleNamespace(versions=[version])
    parsed = SimpleNamespace(table_count=1)
    drafts = [SimpleNamespace(text="테스트 본문")]

    monkeypatch.setattr(document_service, "session_scope", lambda: nullcontext(object()))
    monkeypatch.setattr(
        document_service.document_repo,
        "get_document",
        lambda session, doc_id: document,
    )
    monkeypatch.setattr(parser, "parse", lambda path: parsed)
    monkeypatch.setattr(chunker, "chunk", lambda parsed: drafts)
    monkeypatch.setattr(
        embedder,
        "embed_documents",
        lambda texts: [[0.1, 0.2]],
    )
    monkeypatch.setattr(
        embedder,
        "model_label",
        lambda: "local/bge-m3",
    )
    monkeypatch.setattr(chunker, "summarize", lambda drafts: "테스트 요약")
    monkeypatch.setattr(store, "save_chunks", lambda *args: None)

    result = document_service.ingest_document(
        doc_id="DOC-FI-009",
        version="v2.4",
        path="sample.docx",
    )

    assert version.embed_model == "local/bge-m3"
    assert version.index_status == "완료"
    assert result["chunks"] == 1
    assert result["vectors"] == 1


def test_run_ingest_job_uses_document_id_and_completes_steps(monkeypatch) -> None:
    ingest_args: dict[str, str] = {}

    def fake_ingest_document(*, doc_id: str, version: str, path: str) -> dict:
        ingest_args.update(doc_id=doc_id, version=version, path=path)
        return {
            "chunks": 3,
            "tables": 1,
            "vectors": 3,
            "summary": "테스트 요약",
        }

    monkeypatch.setattr(document_service, "ingest_document", fake_ingest_document)
    job_id = document_service.start_ingest_job(
        doc_id="DOC-FI-009",
        version="v2.4",
        path="sample.docx",
    )

    document_service.run_ingest_job(job_id)
    job = document_service.get_job(job_id)

    assert ingest_args == {
        "doc_id": "DOC-FI-009",
        "version": "v2.4",
        "path": "sample.docx",
    }
    assert job["status"] == "완료"
    assert job["progress"] == 100
    assert job["chunk_count"] == 3
    assert all(step["state"] == "ok" for step in job["steps"])
