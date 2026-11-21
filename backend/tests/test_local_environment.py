"""Integration checks use a temporary SQLite database, never the developer's DB."""
import os
import subprocess
import sys


def run_isolated(tmp_path, code):
    env = {
        key: os.environ[key]
        for key in ("PATH", "HOME", "SYSTEMROOT") if key in os.environ
    }
    env.update({
        "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}",
        "SECRET_KEY": "test-only-secret-key-32-characters-long",
        "REDIS_URL": "redis://localhost:6379/0",
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/0",
        "APP_ENV": "development",
        "DEBUG": "false",
    })
    subprocess.run([sys.executable, "-c", code], env=env, cwd=tmp_path, check=True)


def test_sqlite_initialization_is_idempotent_and_preserves_data(tmp_path):
    run_isolated(tmp_path, '''
import asyncio
from sqlalchemy import text
from app.database import engine, init_db, close_db
async def main():
    await init_db()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE marker (value TEXT)"))
        await conn.execute(text("INSERT INTO marker VALUES ('keep')"))
    await init_db()
    async with engine.connect() as conn:
        assert (await conn.execute(text("SELECT value FROM marker"))).scalar_one() == 'keep'
    await close_db()
asyncio.run(main())
''')


def test_server_health_with_sqlite(tmp_path):
    run_isolated(tmp_path, '''
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    response = client.get('/health')
    assert response.status_code == 200
''')


def test_registration_and_login_with_sqlite(tmp_path):
    run_isolated(tmp_path, '''
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    response = client.post('/api/v1/auth/register', json={
        'email': 'fiction@example.com', 'password': 'fiction-pass-123',  # gitleaks:allow — synthetic test credential
        'full_name': 'Fictional Person', 'organization_name': 'Fiction',
        'organization_slug': 'fiction',
    })
    assert response.status_code == 201, response.text
    response = client.post('/api/v1/auth/login', json={
        'email': 'fiction@example.com', 'password': 'fiction-pass-123',  # gitleaks:allow — synthetic test credential
    })
    assert response.status_code == 200, response.text
    assert response.json()['user']['email'] == 'fiction@example.com'
''')


def test_passlib_bcrypt_round_trip(tmp_path):
    run_isolated(tmp_path, '''
from passlib.context import CryptContext
ctx = CryptContext(schemes=['bcrypt'])
hashed = ctx.hash('example-password')
assert ctx.verify('example-password', hashed)
''')
