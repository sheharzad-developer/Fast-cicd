import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app, repo

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_repo():
    repo.clear()
    yield
    repo.clear()


def make_task(**overrides):
    body = {"title": "Write tests", "priority": "high"} | overrides
    resp = client.post("/tasks", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Health ----------


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------- Create ----------


def test_create_task_returns_201_and_defaults():
    task = make_task(title=" Deploy to AWS ")
    assert task["title"] == "Deploy to AWS"  # whitespace trimmed
    assert task["completed"] is False
    assert uuid.UUID(task["id"])


@pytest.mark.parametrize(
    "body",
    [
        {},  # missing title
        {"title": ""},  # empty
        {"title": " "},  # blank
        {"title": "x" * 201},  # too long
        {"title": "ok", "priority": "urgent"},  # bad enum
        {"title": "ok", "due_date": "not-a-date"},
        {"title": "ok", "unknown": 1},  # extra field
    ],
)
def test_create_task_rejects_invalid_input(body):
    resp = client.post("/tasks", json=body)
    assert resp.status_code == 422
    assert resp.json()["error"] == "validation_error"


# ---------- Read ----------


def test_list_and_filter_tasks():
    make_task(title="A")
    make_task(title="B", completed=True)
    assert len(client.get("/tasks").json()) == 2
    done = client.get("/tasks", params={"completed": True}).json()
    assert [t["title"] for t in done] == ["B"]


def test_get_task_by_id():
    task = make_task()
    resp = client.get(f"/tasks/{task['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == task["id"]


def test_get_missing_task_returns_404():
    resp = client.get(f"/tasks/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"] == "not_found"


def test_get_task_with_bad_uuid_returns_422():
    assert client.get("/tasks/not-a-uuid").status_code == 422


# ---------- Update ----------


def test_update_task_partial():
    task = make_task()
    resp = client.put(f"/tasks/{task['id']}", json={"completed": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["completed"] is True
    assert body["title"] == task["title"]
    assert body["updated_at"] >= task["updated_at"]


def test_update_with_empty_body_returns_422():
    task = make_task()
    assert client.put(f"/tasks/{task['id']}", json={}).status_code == 422


def test_update_missing_task_returns_404():
    resp = client.put(f"/tasks/{uuid.uuid4()}", json={"completed": True})
    assert resp.status_code == 404


# ---------- Delete ----------


def test_delete_task():
    task = make_task()
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_delete_missing_task_returns_404():
    assert client.delete(f"/tasks/{uuid.uuid4()}").status_code == 404
