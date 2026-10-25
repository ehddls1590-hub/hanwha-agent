"""크로스 인코더 리랭커 BAAI/bge-reranker-v2-m3 를 받아 models/ 에 둔다. 

쓰는 법 — 프로젝트 루트(hanhwa-agent)에서, 가상환경을 켠 채로 (맥: py → python3)

    py download_reranker.py              받기 → 확인
    py download_reranker.py --check      받지 않고 확인만 (USB 배포본을 복사한 사람)
    py download_reranker.py --smoke      확인 + 실제로 열어 질문·조각 두 쌍에 점수 매기기
                                          (sentence-transformers 필요)

받는 위치 기본값 = 프로젝트 폴더 바로 옆 models/bge-reranker-v2-m3
다른 위치에 두려면 --dest 로 models 폴더를 준다.

필요한 것: py -m pip install "huggingface-hub>=1.5,<2"  
로그인·토큰은 필요 없다 (공개 저장소 · Apache-2.0). 약 2.3 GB.
받다가 끊기면 같은 명령을 다시 실행한다 — 받은 부분은 남아 있고 이어서 받는다.
"""
import argparse
import os
import shutil
import sys
import time
from pathlib import Path

# 윈도우 cp949 콘솔에서도 글자가 깨지지 않게
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO = "BAAI/bge-reranker-v2-m3"
FOLDER = "bge-reranker-v2-m3"
PATTERNS = ["*.json", "*.safetensors", "sentencepiece.bpe.model"]
NEED_FILES = ["model.safetensors", "config.json", "tokenizer.json",
              "tokenizer_config.json", "special_tokens_map.json", "sentencepiece.bpe.model"]
MIN_WEIGHT_BYTES = 2_000_000_000   # model.safetensors 는 약 2.27 GB — 이보다 작으면 받다가 끊긴 것
NEED_BYTES = 3 * 1024**3           # 받을 양 2.3 GB + 여유


def default_dest() -> Path | None:
    here = Path.cwd()
    if (here / "backend").is_dir() and (here / "pyproject.toml").is_file():
        return here.parent / "models"
    return None


def check(folder: Path) -> bool:
    missing = [f for f in NEED_FILES if not (folder / f).is_file()]
    if missing:
        print(f"  X {folder}")
        for f in missing:
            print(f"      없음 : {f}")
        return False
    weight = (folder / "model.safetensors").stat().st_size
    for p in sorted(folder.iterdir()):
        if p.is_file():
            print(f"    {p.name:<28} {p.stat().st_size / 1024**2:>10,.1f} MB")
    if weight < MIN_WEIGHT_BYTES:
        print(f"  X model.safetensors 가 {weight / 1e9:.2f} GB — 받다가 끊겼습니다. 다시 실행하세요")
        return False
    print(f"  v {folder}  (model.safetensors {weight / 1e9:.2f} GB)")
    return True


def download(folder: Path) -> None:
    if os.environ.pop("HF_HUB_OFFLINE", None):
        print("(HF_HUB_OFFLINE 이 켜져 있어 이 실행에서만 껐습니다)")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        sys.exit('huggingface-hub 가 없습니다 → py -m pip install "huggingface-hub>=1.5,<2"')

    folder.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(folder).free
    if free < NEED_BYTES:
        sys.exit(f"디스크 여유가 {free / 1e9:.1f} GB 입니다 — 3 GB 이상 비우고 다시 실행하세요.")

    print(f"\n[{FOLDER}] {REPO} → {folder}")
    t0 = time.perf_counter()
    for attempt in range(1, 4):
        try:
            snapshot_download(repo_id=REPO, local_dir=folder, allow_patterns=PATTERNS)
            break
        except Exception as e: 
            print(f"  {attempt}회차 실패: {type(e).__name__}: {e}")
            if attempt == 3:
                print("  세 번 실패했습니다. 잠시 뒤 같은 명령을 다시 실행하면 이어서 받습니다.")
                print("  403 · SSL 오류라면 이 인터넷이 Hugging Face 를 막고 있습니다 → 다른 망이나 강사 USB 배포본을 씁니다.")
                sys.exit(1)
            print("  10초 뒤 이어서 받습니다…")
            time.sleep(10)
    print(f"  {time.perf_counter() - t0:.0f}초")


def smoke(folder: Path) -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"   # 수업과 같은 조건 — import 전에
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        sys.exit('sentence-transformers 가 없습니다 → py -m pip install "sentence-transformers==6.0.1"')
    t0 = time.perf_counter()
    model = CrossEncoder(str(folder), max_length=512)
    t1 = time.perf_counter()
    q = "4급 직원이 광역시로 출장 갈 때 숙박비 상한은 얼마인가요?"
    pairs = [(q, "[별표1] 4급 숙박비(광역시) 70,000원"), (q, "정보보안 지침 제5조 접근권한은 보안팀장이 승인한다")]
    scores = model.predict(pairs, activation_fn=None)
    sig = [1 / (1 + pow(2.718281828, -float(s))) for s in scores]
    print(f"  여는 데 {t1 - t0:.1f}초 · 관련 조각 {sig[0]:.2f} · 무관한 조각 {sig[1]:.2f}  ← 앞이 훨씬 크면 정상")


def main() -> int:
    ap = argparse.ArgumentParser(description="bge-reranker-v2-m3 를 models/ 에 받는다")
    ap.add_argument("--dest", type=Path, help="models 폴더 경로 (기본: 프로젝트 폴더 바로 옆)")
    ap.add_argument("--check", action="store_true", help="받지 않고 확인만")
    ap.add_argument("--smoke", action="store_true", help="확인 후 실제로 열어 점수를 매겨 본다")
    args = ap.parse_args()

    dest = args.dest or default_dest()
    if dest is None:
        print("프로젝트 루트(hanhwa-agent)에서 실행하거나 --dest 로 models 폴더를 알려 주세요.")
        print(r"  예) cd C:\dev\hanhwa-agent  →  py download_reranker.py")
        print(r"  예) py download_reranker.py --dest C:\dev\models")
        return 1
    folder = (dest.expanduser().resolve()) / FOLDER
    print(f"모델 폴더: {folder}")

    if not args.check and not args.smoke:
        download(folder)

    print("\n확인")
    if not check(folder):
        return 1
    if args.smoke:
        print("\n열어 보기 (처음에는 몇십 초 걸립니다)")
        smoke(folder)
    print("\n완료. .env 에 RERANKER=cross_encoder 를 넣으면 이 모델을 씁니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
