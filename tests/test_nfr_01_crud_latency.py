import concurrent.futures
import threading
import time
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
counter = 0
lock = threading.Lock()


def increment():
    global counter
    with lock:
        counter += 1
        return counter


def get_future_date(days=1):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


def test_should_write_with_300ms_latency():
    time.sleep(1.2)

    def make_request():
        start_time = time.time()
        topic = {
            "title": f"test_should_write_with_300ms_latency_{increment()}",
            "due_at": get_future_date(increment()),
            "status": "open",
        }
        r = client.post("/topics", json=topic)

        end_time = time.time()

        assert (
            r.status_code == 200
        ), f"Expected 200, got {r.status_code}. Response: {r.text}"

        return (end_time - start_time) * 1000

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    max_duration = max(results)
    assert max_duration <= 300, f"Maximum running time: {max_duration} ms"

    avg_duration = sum(results) / len(results)
    print(f"Average time: {avg_duration:.2f} ms")
    print(f"Maximum time: {max_duration:.2f} ms")
