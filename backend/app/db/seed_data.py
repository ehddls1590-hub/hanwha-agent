from __future__ import annotations

from datetime import date

TEMP_PASSWORD = "qwer1234!"

DEPARTMENTS: list[dict] = [
    {"id": "HR", "name": "경영지원팀"},
    {"id": "HRGA", "name": "인사총무"},
    {"id": "INFRA2", "name": "인프라사업부 2팀"},
    {"id": "PU", "name": "구매팀"},
    {"id": "SE", "name": "보안팀"},
    {"id": "PMO", "name": "PMO"},
]

USERS: list[dict] = [
    {"id": 1, "emp_no": "2019-0412", "name": "김민준", "dept_id": "INFRA2",
     "role": "일반", "clearance": "일반"},
    {"id": 2, "emp_no": "2014-0088", "name": "정현우", "dept_id": "INFRA2",
     "role": "팀장", "clearance": "3급"},
    {"id": 3, "emp_no": "2011-0003", "name": "한서영", "dept_id": "HR",
     "role": "관리자", "clearance": "대외비"},
    {"id": 4, "emp_no": "2016-0231", "name": "김지원", "dept_id": "HRGA",
     "role": "일반", "clearance": "3급"},
    {"id": 5, "emp_no": "2013-0177", "name": "박성호", "dept_id": "PU",
     "role": "팀장", "clearance": "대외비"},
    {"id": 6, "emp_no": "2009-0055", "name": "이재훈", "dept_id": "SE",
     "role": "팀장", "clearance": "대외비"},
    {"id": 7, "emp_no": "2015-0402", "name": "최민석", "dept_id": "PMO",
     "role": "팀장", "clearance": "3급"},
]



DOCUMENTS: list[dict] = [
    {
        "id": "DOC-HR-014", "title": "국내출장 여비 규정", "dept_id": "HRGA",
        "security_level": "일반", "owner_id": 4,
        "versions": [
            {"version": "v2.0", "status": "현행",
             "effective_from": date(2025, 7, 1), "expires_at": None,
             "file_path": "uploads/DOC-HR-014_v2.0.docx", "file_format": "docx",
             "chunk_count": 84, "embed_model": "upstage/embed-2",
             "index_status": "완료", "index_progress": 100,
             "indexed_at": date(2025, 6, 28)},
            {"version": "v1.1", "status": "만료",
             "effective_from": date(2024, 9, 1), "expires_at": date(2025, 6, 30),
             "file_path": "uploads/DOC-HR-014_v1.1.docx", "file_format": "docx",
             "chunk_count": 79, "embed_model": "upstage/embed-2",
             "index_status": "보관", "index_progress": 100,
             "indexed_at": date(2024, 8, 28)},
        ],
    },
    {
        "id": "DOC-HR-002", "title": "복무 규정", "dept_id": "HRGA",
        "security_level": "일반", "owner_id": 4,
        "versions": [
            {"version": "v3.1", "status": "현행",
             "effective_from": date(2026, 1, 1), "expires_at": None,
             "file_path": "uploads/DOC-HR-002_v3.1.pdf", "file_format": "pdf",
             "chunk_count": 112, "embed_model": "upstage/embed-2",
             "index_status": "완료", "index_progress": 100,
             "indexed_at": date(2025, 12, 22)},
        ],
    },
    {
        "id": "DOC-HR-021", "title": "재택근무 운영 지침", "dept_id": "HRGA",
        "security_level": "일반", "owner_id": 3,
        "versions": [
            {"version": "v1.2", "status": "현행",
             "effective_from": date(2025, 11, 1), "expires_at": None,
             "file_path": "uploads/DOC-HR-021_v1.2.docx", "file_format": "docx",
             "chunk_count": 41, "embed_model": "upstage/embed-2",
             "index_status": "완료", "index_progress": 100,
             "indexed_at": date(2025, 10, 27)},
        ],
    },
    {
        "id": "DOC-PU-007", "title": "구매·계약 규정", "dept_id": "PU",
        "security_level": "대외비", "owner_id": 5,
        "versions": [
            {"version": "v4.0", "status": "현행",
             "effective_from": date(2026, 3, 1), "expires_at": None,
             "file_path": "uploads/DOC-PU-007_v4.0.pdf", "file_format": "pdf",
             "chunk_count": 156, "embed_model": "upstage/embed-2",
             "index_status": "완료", "index_progress": 100,
             "indexed_at": date(2026, 2, 24)},
        ],
    },
    {
        "id": "DOC-SE-003", "title": "정보보안 지침", "dept_id": "SE",
        "security_level": "대외비", "owner_id": 6,
        "versions": [
            
            {"version": "v2.2", "status": "현행",
             "effective_from": date(2025, 10, 1), "expires_at": None,
             "file_path": "uploads/DOC-SE-003_v2.2.pdf", "file_format": "pdf",
             "chunk_count": 98, "embed_model": "upstage/embed-2",
             "index_status": "재임베딩", "index_progress": 62,
             "indexed_at": None},
        ],
    },
    {
        "id": "DOC-SE-011", "title": "장비 반출입 절차", "dept_id": "SE",
        "security_level": "3급", "owner_id": 6,
        "versions": [
            {"version": "v1.0", "status": "현행",
             "effective_from": date(2024, 5, 1), "expires_at": date(2026, 12, 31),
             "file_path": "uploads/DOC-SE-011_v1.0.docx", "file_format": "docx",
             "chunk_count": 33, "embed_model": "upstage/embed-2",
             "index_status": "완료", "index_progress": 100,
             "indexed_at": date(2024, 4, 26)},
        ],
    },
    {
        "id": "DOC-PM-005", "title": "프로젝트 관리 지침", "dept_id": "PMO",
        "security_level": "일반", "owner_id": 7,
        "versions": [
            
            {"version": "v2.0", "status": "현행",
             "effective_from": date(2026, 2, 1), "expires_at": None,
             "file_path": "uploads/DOC-PM-005_v2.0.pdf", "file_format": "pdf",
             "chunk_count": 87, "embed_model": None,
             "index_status": "대기", "index_progress": 0,
             "indexed_at": None},
        ],
    },
]
