
import pytest

from app.core.exceptions import (
    AgentError, NotFound, PermissionDenied, ValidationFailed, GuardTripped,
    RateLimited, ExternalServiceError, ModeNotAvailable, ApprovalRequired,
)

CASES = [
    (NotFound, 404, "not_found"),
    (PermissionDenied, 403, "permission_denied"),
    (ValidationFailed, 422, "validation_failed"),
    (GuardTripped, 400, "guard_tripped"),
    (RateLimited, 429, "rate_limited"),
    (ExternalServiceError, 502, "external_service_error"),
    (ModeNotAvailable, 409, "mode_not_available"),
    (ApprovalRequired, 409, "approval_required"),
]


@pytest.mark.parametrize("exc_cls,status,code", CASES)
def test_domain_exception_maps_to_status_and_code(exc_cls, status, code) -> None:
    exc = exc_cls("문서를 찾을 수 없습니다: DOC-HR-014")
    assert exc.status_code == status
    assert exc.code == code


def test_every_domain_exception_is_agent_error() -> None:
    for exc_cls, _status, _code in CASES:
        assert issubclass(exc_cls, AgentError)


def test_detail_is_optional_and_kept(travel_doc) -> None:
    없음 = NotFound(f"문서를 찾을 수 없습니다: {travel_doc['doc_id']}")
    assert 없음.detail is None
    assert 없음.message == "문서를 찾을 수 없습니다: DOC-HR-014"

    있음 = NotFound("문서를 찾을 수 없습니다: DOC-HR-014", detail="인사팀 시드 데이터 누락")
    assert 있음.detail == "인사팀 시드 데이터 누락"