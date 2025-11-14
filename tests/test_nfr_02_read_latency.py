import concurrent.futures
import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_should_get_by_title_with_200ms_latency():
    time.sleep(1.2)
    topic = {
        "title": "test_should_get_by_title_with_200ms_latency",
        "due_at": "2025-10-01T12:00:00",
        "status": "open",
    }
    client.post("/topics", json=topic)

    def make_request():
        start_time = time.time()
        r = client.get("/topics/title/test_should_get_by_title_with_200ms_latency")
        end_time = time.time()

        assert r.status_code == 200
        assert topic == r.json()

        return (end_time - start_time) * 1000

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_request) for _ in range(20)]
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    max_duration = max(results)
    assert max_duration <= 200, f"Maximum running time: {max_duration} ms"

    avg_duration = sum(results) / len(results)
    print(f"Average time: {avg_duration:.2f} ms")
    print(f"Maximum time: {max_duration:.2f} ms")


def test_should_get_by_status_with_200ms_latency():
    time.sleep(1.2)
    topic = {
        "title": "test_should_get_by_status_with_200ms_latency",
        "due_at": "2025-10-01T12:00:00",
        "status": "open",
    }
    client.post("/topics", json=topic)

    def make_request():
        start_time = time.time()
        r = client.get("/topics/status/open")
        end_time = time.time()

        assert r.status_code == 200

        return (end_time - start_time) * 1000

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_request) for _ in range(20)]
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    max_duration = max(results)
    assert max_duration <= 200, f"Maximum running time: {max_duration} ms"

    avg_duration = sum(results) / len(results)
    print(f"Average time: {avg_duration:.2f} ms")
    print(f"Maximum time: {max_duration:.2f} ms")
