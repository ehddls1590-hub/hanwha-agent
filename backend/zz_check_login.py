from app.db.init_db import init_db
from app.db.seed import seed_all
from app.db.session import session_scope
from app.repositories.user_repo import get_by_emp_no

init_db()
seed_all()
with session_scope() as s:
    user = get_by_emp_no(s, "2016-0231")
    print(type(user).__name__ if user else None)
    print(user.emp_no if user else "none")
