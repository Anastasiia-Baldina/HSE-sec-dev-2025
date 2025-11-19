import time
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get_valid_future_date(days=1):
    max_days = min(days, 365)
    return (datetime.now() + timedelta(days=max_days)).strftime("%Y-%m-%dT%H:%M:%S")


def new_topic(i: int) -> dict:
    return {
        "title": f"test_topics_write_rate_limited_to_15_rps_{i}",
        "due_at": get_valid_future_date(1),
        "status": "open",
    }


def test_topics_write_rate_limited_to_15_rps():
    time.sleep(1.2)

    responses = []
    for i in range(16):
        r = client.post("/topics", json=new_topic(i))
        responses.append(r)

    status_codes = [r.status_code for r in responses]
    assert (
        status_codes.count(429) >= 1
    ), f"Expected at least one with 429, but was: {status_codes}"
    assert (
        status_codes[-1] == 429
    ), f"Expected 429 on last request, but was: {status_codes[-1]}"

    time.sleep(1.2)
    r_ok = client.post("/topics", json=new_topic(999))
    assert (
        r_ok.status_code == 200
    ), f"Expected 200 after time window, but was {r_ok.status_code}. Response: {r_ok.text}"
