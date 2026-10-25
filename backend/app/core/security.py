from __future__ import annotations

import bcrypt

# 암호화 : raw 문자열을 주면 암호화된 문자열로 변환하여 리턴 
def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# 검증 : raw문자열과 암호화된 문자열을 주면, 두개가 일치하는지 True/False 돌려주는 함수 
def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
