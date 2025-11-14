import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_should_get_topics_with_rate_limit_on_25_rps():
    time.sleep(1.2)
    topic = {
        "title": "test_should_get_topics_with_rate_limit_on_25_rps",
        "due_at": "2025-10-01T12:00:00",
        "status": "open",
    }
    r = client.post("/topics", json=topic)
    responses = []
    for i in range(26):
        r = client.get("/topics/title/test_should_get_topics_with_rate_limit_on_25_rps")
        responses.append(r)

    status_codes = [r.status_code for r in responses]
    assert (
        status_codes.count(429) >= 1
    ), f"Expected at least one with 429, but was: {status_codes}"
    assert (
        status_codes[-1] == 429
    ), f"Expected 429 on last request, but was: {status_codes[-1]}"

    time.sleep(1.2)
    r_ok = client.get("/topics/title/test_should_get_topics_with_rate_limit_on_25_rps")
    assert (
        r_ok.status_code == 200
    ), f"Expected 200 after time window, but was {r_ok.status_code}"
