"""
PanataanPH Database Initialization Script.

Creates all database tables without inserting any data.
Run from the src/ directory:
    python -m backend.init_db
"""

from backend.database import init_db


def main() -> None:
    print("🔧 Initializing PanataanPH database...")
    init_db()
    print("✅ All tables created successfully.")
    print("💡 To populate with sample data, run: python -m backend.seed")


if __name__ == "__main__":
    main()
