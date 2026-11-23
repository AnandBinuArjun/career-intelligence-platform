import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure test-safe defaults before importing app modules.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limiter
from app.main import app
from app.models.entities import Base


@pytest.fixture()
def client(tmp_path: Path):
    db_file = tmp_path / "test_career.db"
    test_engine = create_engine(
        f"sqlite+pysqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=test_engine)

    prev_storage_backend = settings.storage_backend
    prev_storage_dir = settings.local_storage_dir
    prev_rate_limit = settings.rate_limit_enabled
    prev_ai_mode = settings.ai_routing_mode
    settings.storage_backend = "local"
    settings.local_storage_dir = str(tmp_path / "private_storage")
    settings.rate_limit_enabled = False
    settings.ai_routing_mode = "deterministic"
    rate_limiter.reset()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    settings.storage_backend = prev_storage_backend
    settings.local_storage_dir = prev_storage_dir
    settings.rate_limit_enabled = prev_rate_limit
    settings.ai_routing_mode = prev_ai_mode
    test_engine.dispose()
