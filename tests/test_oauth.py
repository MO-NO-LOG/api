import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_kakao_login_redirects():
    with patch("app.routers.oauth.settings") as mock_settings:
        mock_settings.KAKAO_REST_API_KEY = "fake_key"
        mock_settings.KAKAO_REDIRECT_URI = "https://example.com/callback"
        response = client.get("/api/oauth/kakao/login", follow_redirects=False)
        assert response.status_code in (307, 302)
        assert "kauth.kakao.com" in response.headers["location"]
        assert "client_id=fake_key" in response.headers["location"]
        assert "redirect_uri=https" in response.headers["location"]


def test_kakao_login_not_configured():
    with patch("app.routers.oauth.settings") as mock_settings:
        mock_settings.KAKAO_REST_API_KEY = ""
        mock_settings.KAKAO_REDIRECT_URI = ""
        response = client.get("/api/oauth/kakao/login")
        assert response.status_code == 503


def test_kakao_callback_auth_failure():
    """When Kakao rejects the code, redirect with error."""
    with patch("app.routers.oauth.settings") as mock_settings, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_settings.KAKAO_REST_API_KEY = "key"
        mock_settings.KAKAO_REDIRECT_URI = "uri"
        mock_post.return_value = AsyncMock(status_code=400)

        response = client.get("/api/oauth/kakao/callback?code=fake", follow_redirects=False)
        assert response.status_code in (307, 302)
        assert "error=kakao_auth_failed" in response.headers["location"]
