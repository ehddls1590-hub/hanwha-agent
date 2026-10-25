# 계층 의존 방향 검사 테스트 코드
# api/v1 -> services -> repositories -> models(위에서 밑으로...)
# -> 규칙을 테스트로 만들어서 체크

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

OURS = "app"

# 파일 최상단에서 import하는 모듈 이름을 모으기
def _top_level_imports(path: Path) -> list[str]:

    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):          
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):     
            if node.module:
                names.append(node.module)
    return names

# 계층 폴더 하나 안의 .py 파일을 전부 찾아내기
def _py_files(layer: str) -> list[Path]:
    
    folder = APP / layer
    if not folder.is_dir():
        return []
    return sorted(folder.rglob("*.py"))


# 모듈이 그 패키지에 속하는지 여부 판단
def _is(name: str, prefix: str) -> bool:
    return name == prefix or name.startswith(prefix + ".")

# 한 계층 안에서 금지된 import하는 모듈 이름을 모으기
def _violations(
    layer: str,
    forbidden: tuple[str, ...],
    allowed: tuple[str, ...] = (),
) -> list[str]:
    found: list[str] = []
    for path in _py_files(layer):
        for name in _top_level_imports(path):
            if not _is(name, OURS):
                continue                                  # 외부 패키지는 관심 밖
            if any(_is(name, ok) for ok in allowed):
                continue
            if any(_is(name, bad) for bad in forbidden):
                found.append(f"{path.relative_to(APP)} → {name}")
    return found

# 모델은 최 하위 계층이라, 우리 앱의 다른 계층을 모른다. 우리의 다른 계층을 역으로 부르는지 검사
def test_models_import_nothing_but_models() -> None:
    offenders = _violations("models", forbidden=(OURS,), allowed=("app.models",))
    assert not offenders, (
        "models 가 다른 계층을 import 합니다. 모델은 맨 아래층이라 아무도 올려다보지 "
        "않습니다. 필요한 값은 인자로 받고, 규칙은 services 로 올리세요:\n  "
        + "\n  ".join(offenders)
    )

# 라우터에서 한 층 건너뛰어 DB 꼐층을 직접 부르지 않게 검사
def test_api_does_not_import_repositories_or_models() -> None:
    offenders = _violations("api/v1", forbidden=("app.repositories", "app.models"))
    assert not offenders, (
        "라우터가 repositories/models 를 직접 import 합니다. 그 호출을 services 의 "
        "함수로 옮기고 라우터는 그 함수만 부르세요:\n  " + "\n  ".join(offenders)
    )

# 서비스에서 API 라우터 임포트 하지 않게 검사
def test_services_do_not_import_api() -> None:
    offenders = _violations("services", forbidden=("app.api",))
    assert not offenders, (
        "services 가 api 를 import 합니다. 의존이 거꾸로 섰습니다. 필요한 값은 "
        "라우터가 인자로 내려 주게 바꾸세요:\n  " + "\n  ".join(offenders)
    )

# 리포지토리는 DB만 다룬다. 서비스 또는 API 라우터를 임포트하지 않게 검사
def test_repositories_do_not_import_services_or_api() -> None:
    offenders = _violations("repositories", forbidden=("app.services", "app.api"))
    assert not offenders, (
        "repositories 가 services/api 를 import 합니다. 판단은 services 에 두고 "
        "리포지토리는 값만 돌려주세요:\n  " + "\n  ".join(offenders)
    )

# 외부 연동은 factory 한 곳으로만 들어가도록 검사
def test_services_reach_integrations_only_through_factory() -> None:
    offenders = _violations(
        "services",
        forbidden=("app.integrations",),
        allowed=("app.integrations.factory",),
    )
    assert not offenders, (
        "services 가 어댑터를 직접 import 합니다. integrations/factory.py 를 거쳐 "
        "Protocol 타입으로만 받으세요:\n  " + "\n  ".join(offenders)
    )

