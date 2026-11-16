import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["ENVIRONMENT"] = "test"
temp_dir = tempfile.mkdtemp()
os.environ["DATA_DIR"] = temp_dir

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.config import settings
from backend.app.models.user import User
from backend.app.core.security import hash_password, create_user_session
from backend.app.services.vector_store import vector_store_service

test_db_path = Path(temp_dir) / "test.db"
test_engine = create_engine(
    f"sqlite:///{test_db_path.as_posix()}",
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def admin_user(db):
    user = db.query(User).filter(User.username == "admin_test").first()
    if not user:
        user = User(
            username="admin_test",
            email="admin_test@forgetcheck.local",
            hashed_password=hash_password("AdminPass123!"),
            role="admin",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@pytest.fixture
def member_user(db):
    user = db.query(User).filter(User.username == "member_test").first()
    if not user:
        user = User(
            username="member_test",
            email="member_test@forgetcheck.local",
            hashed_password=hash_password("MemberPass123!"),
            role="member",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@pytest.fixture
def auth_headers(db, admin_user):
    session = create_user_session(db, admin_user)
    return {"Authorization": f"Bearer {session.session_token}"}

@pytest.fixture
def member_auth_headers(db, member_user):
    session = create_user_session(db, member_user)
    return {"Authorization": f"Bearer {session.session_token}"}
