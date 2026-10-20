import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./unused-test-default.db")
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-not-for-deployment")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    database_url = settings.test_database_url or "sqlite://"
    engine_options = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_options["poolclass"] = StaticPool
    engine = create_engine(database_url, **engine_options)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    original_limiter_state = app.state.limiter.enabled

    def override_get_db():
        db = TestingSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.limiter.enabled = False
    try:
        with TestClient(app) as test_client:
            yield test_client, TestingSession
    finally:
        app.dependency_overrides.clear()
        app.state.limiter.enabled = original_limiter_state
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def register(client: TestClient, name: str, email: str, password: str = "secure-pass123") -> dict:
    response = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str, password: str = "secure-pass123") -> dict:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["user"]
