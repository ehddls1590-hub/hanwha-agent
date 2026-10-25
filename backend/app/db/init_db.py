from __future__ import annotations
from sqlalchemy import Engine
from app.db.session import get_engine

def init_db(engine: Engine | None = None) -> None:

    from app.models import Base
    Base.metadata.create_all(engine or get_engine())


def main() -> None:
    init_db()
    print("테이블 생성 완료")

if __name__ == "__main__":
    main()