from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.seed_data import DEPARTMENTS, DOCUMENTS, TEMP_PASSWORD, USERS
from app.db.session import session_scope
from app.models import Department, Document, DocumentVersion, User


def count_rows(session: Session) -> dict[str, int]:

    return {
        "departments": session.scalar(select(func.count()).select_from(Department)) or 0,
        "users": session.scalar(select(func.count()).select_from(User)) or 0,
        "documents": session.scalar(select(func.count()).select_from(Document)) or 0,
        "versions": session.scalar(select(func.count()).select_from(DocumentVersion)) or 0,
    }


def seed_all(session: Session | None = None) -> dict[str, int]:
    if session is not None:
        return _seed(session)
    with session_scope() as s:
        return _seed(s)


def _seed(session: Session) -> dict[str, int]:

    if session.scalar(select(func.count()).select_from(Document)):
        return count_rows(session)

    session.add_all(Department(**row) for row in DEPARTMENTS)


    temp_hash = hash_password(TEMP_PASSWORD)
    session.add_all(User(**row, password_hash=temp_hash) for row in USERS)
    session.flush()   

    for doc in DOCUMENTS:
        
        fields = {k: v for k, v in doc.items() if k != "versions"}
        session.add(Document(**fields))
        session.flush()
        session.add_all(
            DocumentVersion(doc_id=doc["id"], **ver) for ver in doc["versions"]
        )
    session.flush()

    return count_rows(session)
