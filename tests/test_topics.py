from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get_future_date(days=30):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


def test_should_create_topic():
    topic = {
        "title": "test_should_create_topic",
        "due_at": get_future_date(1),  # Завтра
        "status": "open",
    }
    r = client.post("/topics", json=topic)
    assert 200 == r.status_code


def test_should_get_by_title():
    topic = {
        "title": "test_should_get_by_title",
        "due_at": get_future_date(2),
        "status": "open",
    }
    client.post("/topics", json=topic)
    r = client.get("/topics/title/test_should_get_by_title")
    assert 200 == r.status_code
    body = r.json()
    assert topic == body


def test_should_return_404_on_get_by_title_when_does_not_exists():
    r = client.get(
        "/topics/title/test_should_return_404_on_get_by_title_when_does_not_exists"
    )
    assert 404 == r.status_code
    body = r.json()
    # Check RFC 7807 format
    assert body["title"] == "not_found"
    assert body["detail"] == "topic not found"
    assert "correlation_id" in body


def test_should_not_create_topic_when_topic_already_exists():
    topic = {
        "title": "test_should_not_create_topic_when_topic_already_exists",
        "due_at": get_future_date(3),
        "status": "open",
    }
    topic2 = {
        "title": "test_should_not_create_topic_when_topic_already_exists",
        "due_at": get_future_date(10),
        "status": "in_progress",
    }

    client.post("/topics", json=topic)
    r = client.post("/topics", json=topic2)
    assert 409 == r.status_code
    body = r.json()
    # Check RFC 7807 format instead of old "error" field
    assert body["title"] == "already_exists"
    assert body["detail"] == "topic already exists"
    assert "correlation_id" in body


def test_should_update_topic():
    topic = {
        "title": "test_should_update_topic",
        "due_at": get_future_date(5),
        "status": "open",
    }
    expected_topic = {
        "title": "test_should_update_topic",
        "due_at": get_future_date(15),
        "status": "in_progress",
    }

    client.post("/topics", json=topic)
    r = client.put("/topics", json=expected_topic)
    assert 200 == r.status_code
    r = client.get("/topics/title/test_should_update_topic")
    assert 200 == r.status_code
    body = r.json()
    assert expected_topic == body


def test_should_not_update_when_topic_does_not_exists():
    topic = {
        "title": "test_should_not_update_when_topic_does_not_exists",
        "due_at": get_future_date(7),
        "status": "open",
    }
    r = client.put("/topics", json=topic)
    assert 404 == r.status_code
    body = r.json()
    # Check RFC 7807 format
    assert body["title"] == "not_found"
    assert body["detail"] == "topic not found"
    assert "correlation_id" in body


def test_should_return_not_found_on_delete_when_topic_does_not_exists():
    r = client.delete(
        "/topics/test_should_return_not_found_on_delete_when_topic_does_not_exists"
    )
    assert 404 == r.status_code
    body = r.json()
    # Check RFC 7807 format instead of old "error" field
    assert body["title"] == "not_found"
    assert body["detail"] == "topic not found"
    assert "correlation_id" in body


def test_should_delete_topic():
    topic = {
        "title": "test_should_delete_topic",
        "due_at": get_future_date(8),
        "status": "open",
    }
    client.post("/topics", json=topic)
    r = client.delete("/topics/test_should_delete_topic")
    assert 200 == r.status_code
    r = client.get("/topics/title/test_should_delete_topic")
    assert 404 == r.status_code


def test_should_find_by_status():
    topic = {
        "title": "test_should_find_by_status",
        "due_at": get_future_date(12),
        "status": "closed",
    }
    client.post("/topics", json=topic)
    r = client.get("/topics/status/closed")
    assert 200 == r.status_code
    body = r.json()
    assert isinstance(body, list)
    assert topic == list(body)[0]
