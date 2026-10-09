"""Create a reviewer only in Playwright's disposable database."""

from pathlib import Path

from backend.auth import hash_password
from backend.database import DATABASE_PATH, SessionLocal, init_db
from backend.models import User


if __name__ == "__main__":
    scratch = Path(__file__).resolve().parents[1] / ".e2e"
    if not Path(DATABASE_PATH).resolve().is_relative_to(scratch.resolve()):
        raise SystemExit("Browser fixtures require a disposable .e2e database")
    init_db()
    with SessionLocal() as db:
        db.add(User(name="Browser Test Reviewer", email="reviewer@example.test", role="lgu", verified=True,
                    password_hash=hash_password("browser-reviewer-password-123")))
        db.commit()
