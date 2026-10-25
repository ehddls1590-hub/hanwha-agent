from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


_ENGINES: dict[str, Engine] = {}


def get_engine(url: str | None = None) -> Engine:

    # 이미 만들어진 엔진이라면 만들어진 것 리턴하며 종료 처리
    resolved = url or get_settings().database_url # 환경변수에서 DB URL 가져와 적용
    if resolved in _ENGINES:
        return _ENGINES[resolved] 

    # SQLite  설정 추가
    connect_args: dict[str, object] = {}
    is_sqlite = resolved.startswith("sqlite")
    if is_sqlite:
        connect_args["check_same_thread"] = False

    # 엔진 생성
    engine = create_engine(resolved, connect_args=connect_args)

    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:  
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # 새로 만들어진 엔진 저장하며 리턴
    _ENGINES[resolved] = engine
    return engine

# 세션 공장 생성 함수
def get_sessionmaker(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or get_engine(), expire_on_commit=False)

# 세션 생성 및  scope 편의 메서드
@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

