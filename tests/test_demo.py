from fastapi.testclient import TestClient

from quantstream.demo import DemoBook, create_demo_app


def test_seed_closes_candles_and_can_alert():
    book = DemoBook()
    book.seed(minutes=6)
    assert book.candles
    assert any(candle.symbol == "AAPL" for candle in book.candles)
    assert book.alerts


def test_demo_page_and_state():
    book = DemoBook()
    book.seed(minutes=2)
    app = create_demo_app(book)
    with TestClient(app) as client:
        page = client.get("/")
        state = client.get("/demo/state")
    assert page.status_code == 200
    assert "QuantStream" in page.text
    assert state.status_code == 200
    assert "candles" in state.json()
