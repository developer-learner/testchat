"""Tests for the served chat page at GET / (src/main.py + src/static/index.html).

Pins AC-1, AC-2. Observes only the locked entry point `src.main:app` and the
locked route `GET /`. Deep DOM/JS behavior (bubble rendering) is validated by
the CEO using the prototype live, not here.
"""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_root_serves_html_page():
    # AC-1: root returns an HTML document.
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_page_wires_chat_endpoint():
    # AC-2: the page wires to the API through its script asset — the page
    # must load the app script, and that script (served by this same app)
    # must reference the endpoint it POSTs to, so page<->API wiring cannot
    # silently break. (v14: the M7 split moved the JS to /static/app.js.)
    r = client.get("/")
    assert "/static/app.js" in r.text
    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert "/api/v1/chat" in js.text
