#!/usr/bin/env python3
"""
Seed script for ForgetCheck.
Seeds demo accounts (admin, auditor, member) and sample departmental documents.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.user import User
from backend.app.core.security import hash_password
from backend.app.services.document_service import document_service
from backend.app.services.synthetic_runner import synthetic_runner

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("[Seed] Initializing ForgetCheck demo data...")

        # 1. Seed Accounts
        accounts = [
            ("admin", "admin@forgetcheck.local", "Admin@ForgetCheck2026!", "admin"),
            ("auditor", "auditor@forgetcheck.local", "Auditor@ForgetCheck2026!", "auditor"),
            ("member", "member@forgetcheck.local", "Member@ForgetCheck2026!", "member")
        ]

        for username, email, pwd, role in accounts:
            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                u = User(
                    username=username,
                    email=email,
                    hashed_password=hash_password(pwd),
                    role=role,
                    is_active=True
                )
                db.add(u)
                print(f" - Created {role} user: {username}")
        db.commit()

        # 2. Seed Synthetic Fixtures
        synthetic_runner.ensure_fixtures_seeded(db)
        print(" - Seeded 20 synthetic scenario fixtures.")

        # 3. Seed Sample Production Documents for Playground
        admin_user = db.query(User).filter(User.username == "admin").first()
        admin_id = admin_user.id if admin_user else None

        sample_docs = [
            (
                "Employee Handbook & Wellness Benefits 2026",
                "HR",
                (
                    "All full-time employees are provided CarePlus Platinum health insurance coverage. "
                    "Annual wellness stipends of $600 are available for fitness memberships and mental health apps. "
                    "Flexible working hours operate between 8:00 AM and 7:00 PM local time. "
                    "Parental leave provides 16 weeks of fully paid leave for all eligible caregivers."
                ),
                ["general_employee", "hr_manager", "admin"]
            ),
            (
                "Corporate Travel and Expense Reimbursement Guidelines",
                "Finance",
                (
                    "Business travel expenses must be pre-approved by your department manager. "
                    "Domestic daily meal per diem is capped at $85 per day. "
                    "Expense reports must be filed within 30 days of trip conclusion via the finance portal. "
                    "First-class air travel is strictly restricted to flights exceeding 8 continuous hours."
                ),
                ["general_employee", "finance_team", "admin"]
            ),
            (
                "Engineering Architecture & API Security Standards",
                "Engineering",
                (
                    "All production services must authenticate using mTLS with short-lived certificates. "
                    "Database access must use connection pooling with TLS 1.3 encryption in transit. "
                    "API rate limiting defaults to 100 requests per minute per IP for unauthenticated traffic "
                    "and 1,000 requests per minute for authenticated API tokens."
                ),
                ["engineering_lead", "devops_team", "admin"]
            )
        ]

        for title, dept, text, principals in sample_docs:
            existing_doc = db.query(User).filter(User.username == title).first()
            try:
                document_service.ingest_document(
                    db=db,
                    title=title,
                    department=dept,
                    raw_text=text,
                    permitted_principals=principals,
                    uploader_id=admin_id
                )
                print(f" - Ingested document: {title}")
            except Exception as e:
                # Document may already be indexed
                pass

        print("[Seed] Seeding completed successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
