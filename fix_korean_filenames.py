"""한글 파일명의 자소 분리(NFD)를 정상 형태(NFC)로 되돌린다.

쓰는 곳 — 맥에서 만든 압축 파일이나 맥에서 올린 파일을 윈도우에서 받았더니
          파일 이름이 'ㄱㅜㄱㄴㅐ…' 처럼 풀어져 보일 때.
          맥·윈도우 어디서 돌려도 되고, 여러 번 돌려도 안전하다.

사용법
    python fix_korean_filenames.py 폴더경로            ← 바로 고친다
    python fix_korean_filenames.py 폴더경로 --dry-run  ← 무엇이 바뀔지 보기만 한다

    (맥은 python 대신 python3)
"""
import argparse
import sys
import unicodedata
from pathlib import Path


def to_nfc(name: str) -> str:
    """이름을 NFC(완성형)로 바꾼다. 이미 NFC 면 그대로 돌려준다."""
    return unicodedata.normalize("NFC", name)


def fix_folder(root: Path, dry_run: bool = False) -> tuple[int, int]:
    """root 아래 모든 파일·폴더 이름을 NFC 로 바꾼다. (바꾼 수, 건너뛴 수) 를 돌려준다."""
    changed = skipped = 0

    # 깊은 곳부터 고친다 - 폴더 이름을 먼저 바꾸면 그 안의 경로가 달라져 못 찾는다
    paths = sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True)

    for path in paths:
        new_name = to_nfc(path.name)
        if new_name == path.name:
            continue                                  # 이미 정상

        target = path.with_name(new_name)
        shown = path.relative_to(root).with_name(new_name)

        # 윈도우에서는 NFD 이름과 NFC 이름이 '다른 파일'로 둘 다 있을 수 있다
        # → 덮어쓰지 않고 알려만 준다
        if target.exists() and not target.samefile(path):
            print(f"  건너뜀 (같은 이름이 이미 있음) : {shown}")
            skipped += 1
            continue

        if dry_run:
            print(f"  바꿀 예정 : {shown}")
        else:
            # 맥은 NFD·NFC 를 같은 이름으로 취급하므로 임시 이름을 거쳐 두 번에 바꾼다
            temp = path.with_name(path.name + ".__nfc_tmp__")
            path.rename(temp)
            temp.rename(target)
            print(f"  바꿈 : {shown}")
        changed += 1

    return changed, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="한글 파일명 자소 분리(NFD) → NFC 로 되돌리기")
    parser.add_argument("folder", help="고칠 폴더 경로")
    parser.add_argument("--dry-run", action="store_true", help="바꾸지 않고 목록만 본다")
    args = parser.parse_args()

    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"폴더가 아닙니다 : {root}")

    print(f"대상 폴더 : {root}")
    changed, skipped = fix_folder(root, dry_run=args.dry_run)

    verb = "바꿀 예정" if args.dry_run else "바꿈"
    print(f"\n{verb} {changed}건 · 건너뜀 {skipped}건")
    if changed == 0 and skipped == 0:
        print("모든 이름이 이미 정상(NFC)입니다.")


if __name__ == "__main__":
    main()
