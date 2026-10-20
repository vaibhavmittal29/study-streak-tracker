"""Tests verifying static asset serving and frontend dashboard bootstrap."""

from fastapi.testclient import TestClient


def test_index_html_serving(client: TestClient) -> None:
    """Verify GET / returns 200 with HTML containing title and app container."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Study Streak Tracker</title>" in response.text
    assert "Study Streak Tracker" in response.text
    assert "id=\"session-form\"" in response.text


def test_static_assets_serving(client: TestClient) -> None:
    """Verify static CSS, JS, and vendored Chart.js are served correctly."""
    css_res = client.get("/static/styles.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers["content-type"]

    js_res = client.get("/static/app.js")
    assert js_res.status_code == 200

    chart_res = client.get("/static/vendor/chart.umd.min.js")
    assert chart_res.status_code == 200
