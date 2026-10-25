import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def travel_doc() -> dict:
    return {
        "doc_id": "DOC-HR-014",
        "title": "국내출장 여비 규정",
        "dept": "인사",
        "version": "v2.0",
        "security_level": "일반",
        "file_format": "docx",
        "status": "현행",
    }


@pytest.fixture
def client():                       
    with TestClient(app) as c:
        yield c