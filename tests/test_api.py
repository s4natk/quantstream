from fastapi.testclient import TestClient

from quantstream.api import create_app


class StubReader:
    async def candles(self, symbol: str):
        return []

    async def alerts(self, symbol: str):
        return []


def test_health_route_is_ok():
    with TestClient(create_app(StubReader())) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
