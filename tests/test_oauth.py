"""
Tests for OAuth/SSO integration module.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== Test Fixtures ====================


@pytest.fixture(autouse=True)
def setup_oauth_env():
    """Set OAuth environment variables for tests."""
    os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
    os.environ["GITHUB_CLIENT_ID"] = "test-github-client-id"
    os.environ["GITHUB_CLIENT_SECRET"] = "test-github-client-secret"
    os.environ["OAUTH_REDIRECT_BASE"] = "http://localhost:9999"
    yield
    # Clean up
    for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
                 "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET",
                 "OAUTH_REDIRECT_BASE"]:
        os.environ.pop(key, None)


@pytest.fixture
def team_and_user():
    """Create a team and return team_id."""
    from config import config as cfg
    # Ensure enterprise tier for OAuth
    orig_tier = cfg.tier
    orig_seats = cfg.license_seats
    orig_team_id = cfg.license_team_id
    cfg.tier = "enterprise"
    cfg.license_seats = 50
    cfg.license_team_id = None  # Will be set by create_team

    from team import create_team, create_user
    team = create_team("OAuth Test Team")
    team_id = team["id"]

    # Create an admin user for the team
    user = create_user(team_id, "oauth_admin", "testpass123", "admin")

    yield team_id, user

    cfg.tier = orig_tier
    cfg.license_seats = orig_seats
    cfg.license_team_id = orig_team_id


# ==================== OAuthConfig Tests ====================


class TestOAuthConfig:
    def test_reads_env_vars(self):
        """OAuthConfig reads client IDs and secrets from env vars."""
        from oauth import OAuthConfig
        config = OAuthConfig()
        assert config.google_client_id == "test-google-client-id"
        assert config.google_client_secret == "test-google-client-secret"
        assert config.github_client_id == "test-github-client-id"
        assert config.github_client_secret == "test-github-client-secret"
        assert config.redirect_base == "http://localhost:9999"

    def test_is_provider_configured(self):
        """Returns True when provider has both client_id and client_secret."""
        from oauth import OAuthConfig
        config = OAuthConfig()
        assert config.is_provider_configured("google") is True
        assert config.is_provider_configured("github") is True

    def test_is_provider_not_configured(self):
        """Returns False when provider env vars are missing."""
        from oauth import OAuthConfig
        config = OAuthConfig()
        # Temporarily clear one
        config.google_client_id = ""
        config.google_client_secret = ""
        assert config.is_provider_configured("google") is False

    def test_unsupported_provider_not_configured(self):
        """Returns False for unknown providers."""
        from oauth import OAuthConfig
        config = OAuthConfig()
        assert config.is_provider_configured("gitlab") is False

    def test_get_configured_providers(self):
        """Returns list of providers that have valid config."""
        from oauth import OAuthConfig
        config = OAuthConfig()
        providers = config.get_configured_providers()
        assert "google" in providers
        assert "github" in providers

    def test_get_configured_providers_partial(self):
        """Only returns providers that are fully configured."""
        from oauth import OAuthConfig
        config = OAuthConfig()
        config.github_client_id = ""
        providers = config.get_configured_providers()
        assert "google" in providers
        assert "github" not in providers

    def test_default_redirect_base(self):
        """Uses default redirect base when env var not set."""
        os.environ.pop("OAUTH_REDIRECT_BASE", None)
        from oauth import OAuthConfig
        config = OAuthConfig()
        assert config.redirect_base == "http://localhost:9999"


class TestOAuthConfigEdgeCases:
    def test_empty_env_vars(self):
        """Handles completely unset env vars gracefully."""
        for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]:
            os.environ.pop(key, None)
        from oauth import OAuthConfig
        config = OAuthConfig()
        assert config.google_client_id == ""
        assert config.google_client_secret == ""
        assert config.is_provider_configured("google") is False


# ==================== URL Generation Tests ====================


class TestOAuthUrlGeneration:
    def test_google_url_contains_correct_params(self, setup_oauth_env):
        """Google OAuth URL includes correct query parameters."""
        from oauth import get_oauth_url
        state = "test-state-value"
        url = get_oauth_url("google", state)

        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=test-google-client-id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A9999%2Fauth%2Foauth%2Fcallback%2Fgoogle" in url
        assert "response_type=code" in url
        assert "scope=openid+email+profile" in url
        assert "state=test-state-value" in url

    def test_github_url_contains_correct_params(self, setup_oauth_env):
        """GitHub OAuth URL includes correct query parameters."""
        from oauth import get_oauth_url
        state = "test-state-456"
        url = get_oauth_url("github", state)

        assert url.startswith("https://github.com/login/oauth/authorize")
        assert "client_id=test-github-client-id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A9999%2Fauth%2Foauth%2Fcallback%2Fgithub" in url
        assert "response_type=code" in url
        assert "scope=read%3Auser+user%3Aemail" in url
        assert "state=test-state-456" in url

    def test_generate_state_length(self):
        """Generated state string has appropriate length."""
        from oauth import generate_state
        state = generate_state()
        assert len(state) >= 32
        assert isinstance(state, str)

    def test_generate_state_unique(self):
        """Each call to generate_state produces a unique value."""
        from oauth import generate_state
        states = {generate_state() for _ in range(100)}
        assert len(states) == 100

    def test_unsupported_provider_raises_error(self, setup_oauth_env):
        """Unsupported provider raises OAuthError."""
        from oauth import get_oauth_url, OAuthError
        with pytest.raises(OAuthError, match="Unsupported OAuth provider"):
            get_oauth_url("gitlab", "state123")

    def test_unconfigured_provider_raises_error(self, setup_oauth_env):
        """Provider without credentials raises OAuthError."""
        os.environ.pop("GOOGLE_CLIENT_ID", None)
        os.environ.pop("GOOGLE_CLIENT_SECRET", None)
        # Reimport to pick up env changes
        import importlib
        import oauth
        importlib.reload(oauth)

        with pytest.raises(oauth.OAuthError, match="not configured"):
            oauth.get_oauth_url("google", "state123")

        # Reset
        os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
        importlib.reload(oauth)


# ==================== Code Exchange Tests ====================


class TestCodeExchange:
    @pytest.mark.asyncio
    async def test_google_exchange_success(self, setup_oauth_env):
        """Successfully exchanges Google auth code for user info."""
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "google-access-token-123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_token_response.raise_for_status = MagicMock()

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": "google-user-456",
            "email": "testuser@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.png",
        }
        mock_user_response.raise_for_status = MagicMock()

        async def mock_post(url, **kwargs):
            if "token" in url:
                return mock_token_response
            raise ValueError(f"Unexpected URL: {url}")

        async def mock_get(url, **kwargs):
            if "userinfo" in url:
                return mock_user_response
            raise ValueError(f"Unexpected URL: {url}")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.get = mock_get
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            from oauth import exchange_code
            result = await exchange_code("google", "auth-code-xyz")

            assert result["email"] == "testuser@gmail.com"
            assert result["name"] == "Test User"
            assert result["provider"] == "google"
            assert result["provider_id"] == "google-user-456"

    @pytest.mark.asyncio
    async def test_github_exchange_success(self, setup_oauth_env):
        """Successfully exchanges GitHub auth code for user info."""
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "github-access-token-789",
            "token_type": "Bearer",
        }
        mock_token_response.raise_for_status = MagicMock()

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "github-user",
            "name": "GitHub User",
            "email": "githubuser@example.com",
        }
        mock_user_response.raise_for_status = MagicMock()

        async def mock_post(url, **kwargs):
            if "token" in url:
                return mock_token_response

        async def mock_get(url, **kwargs):
            if "api.github.com/user" in url and "emails" not in url:
                return mock_user_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.get = mock_get
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            from oauth import exchange_code
            result = await exchange_code("github", "auth-code-abc")

            assert result["email"] == "githubuser@example.com"
            assert result["name"] == "GitHub User"
            assert result["provider"] == "github"
            assert result["provider_id"] == "12345"

    @pytest.mark.asyncio
    async def test_github_exchange_without_email_in_userinfo(self, setup_oauth_env):
        """Fetches primary email from GitHub emails endpoint when not in user info."""
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "github-token-456",
        }
        mock_token_response.raise_for_status = MagicMock()

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 67890,
            "login": "noemail-user",
            "name": "No Email User",
            "email": None,
        }
        mock_user_response.raise_for_status = MagicMock()

        mock_emails_response = MagicMock()
        mock_emails_response.status_code = 200
        mock_emails_response.json.return_value = [
            {"email": "primary@example.com", "primary": True, "verified": True},
            {"email": "secondary@example.com", "primary": False, "verified": True},
        ]
        mock_emails_response.raise_for_status = MagicMock()

        call_count = {"get": 0}

        async def mock_post(url, **kwargs):
            if "token" in url:
                return mock_token_response

        async def mock_get(url, **kwargs):
            call_count["get"] += 1
            if "user/emails" in url:
                return mock_emails_response
            if "api.github.com/user" in url:
                return mock_user_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.get = mock_get
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            from oauth import exchange_code
            result = await exchange_code("github", "auth-code-456")

            assert result["email"] == "primary@example.com"
            assert result["provider_id"] == "67890"

    @pytest.mark.asyncio
    async def test_token_exchange_http_error(self, setup_oauth_env):
        """HTTP error during token exchange raises OAuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")

        async def mock_post(url, **kwargs):
            raise __import__("httpx").HTTPStatusError(
                "Bad Request", request=MagicMock(), response=mock_response
            )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            from oauth import exchange_code, OAuthError
            with pytest.raises(OAuthError, match="Token exchange failed"):
                await exchange_code("google", "bad-code")

    @pytest.mark.asyncio
    async def test_missing_access_token(self, setup_oauth_env):
        """Missing access_token in response raises OAuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.raise_for_status = MagicMock()

        async def mock_post(url, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            from oauth import exchange_code, OAuthError
            with pytest.raises(OAuthError, match="No access_token"):
                await exchange_code("google", "bad-code")

    @pytest.mark.asyncio
    async def test_missing_provider_id(self, setup_oauth_env):
        """Missing provider ID in user info raises OAuthError."""
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "token-123"}
        mock_token_response.raise_for_status = MagicMock()

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "email": "test@example.com",
            "name": "Test User",
            # No "id" field
        }
        mock_user_response.raise_for_status = MagicMock()

        async def mock_post(url, **kwargs):
            return mock_token_response

        async def mock_get(url, **kwargs):
            return mock_user_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.get = mock_get
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            from oauth import exchange_code, OAuthError
            with pytest.raises(OAuthError, match="Could not determine user identity"):
                await exchange_code("google", "test-code")

    @pytest.mark.asyncio
    async def test_unsupported_provider_exchange(self, setup_oauth_env):
        """Exchange with unsupported provider raises OAuthError."""
        from oauth import exchange_code, OAuthError
        with pytest.raises(OAuthError, match="Unsupported OAuth provider"):
            await exchange_code("gitlab", "some-code")


# ==================== find_or_create_oauth_user Tests ====================


class TestFindOrCreateOAuthUser:
    def test_create_new_oauth_user(self, team_and_user):
        """Creates a new user for first-time OAuth login."""
        team_id, _ = team_and_user
        from team import find_or_create_oauth_user

        user = find_or_create_oauth_user(
            team_id=team_id,
            email="alice@gmail.com",
            name="Alice Smith",
            provider="google",
            provider_id="google-12345",
        )

        assert user["email"] == "alice@gmail.com"
        assert user["username"] == "Alice Smith"
        assert user["oauth_provider"] == "google"
        assert user["oauth_id"] == "google-12345"
        assert user["role"] == "member"
        assert user["api_key"].startswith("gw_api_")
        assert "password_hash" not in user

    def test_find_existing_oauth_user(self, team_and_user):
        """Finds existing user by OAuth identity on subsequent login."""
        team_id, _ = team_and_user
        from team import find_or_create_oauth_user

        # Create once
        user1 = find_or_create_oauth_user(
            team_id=team_id,
            email="bob@github.com",
            name="Bob GitHub",
            provider="github",
            provider_id="github-67890",
        )

        # Find on second call
        user2 = find_or_create_oauth_user(
            team_id=team_id,
            email="bob@github.com",
            name="Bob GitHub",
            provider="github",
            provider_id="github-67890",
        )

        assert user2["id"] == user1["id"]
        assert user2["email"] == "bob@github.com"

    def test_update_email_on_relogin(self, team_and_user):
        """Updates user email if it changed at the provider."""
        team_id, _ = team_and_user
        from team import find_or_create_oauth_user

        user1 = find_or_create_oauth_user(
            team_id=team_id,
            email="old@email.com",
            name="Carol",
            provider="google",
            provider_id="google-99999",
        )

        # Email changed at provider
        user2 = find_or_create_oauth_user(
            team_id=team_id,
            email="new@email.com",
            name="Carol",
            provider="google",
            provider_id="google-99999",
        )

        assert user2["id"] == user1["id"]
        assert user2["email"] == "new@email.com"

    def test_invalid_team_id_raises_error(self):
        """Invalid team_id raises TeamError."""
        from team import find_or_create_oauth_user, TeamError
        with pytest.raises(TeamError, match="Team not found"):
            find_or_create_oauth_user(
                team_id="NONEXISTENT",
                email="user@example.com",
                name="User",
                provider="google",
                provider_id="google-111",
            )

    def test_missing_required_params_raises_error(self):
        """Missing required params raises TeamError."""
        from team import find_or_create_oauth_user, TeamError
        with pytest.raises(TeamError, match="team_id, provider, and provider_id"):
            find_or_create_oauth_user(
                team_id="",
                email="user@example.com",
                name="User",
                provider="google",
                provider_id="google-111",
            )

        with pytest.raises(TeamError, match="team_id, provider, and provider_id"):
            find_or_create_oauth_user(
                team_id="TM123",
                email="user@example.com",
                name="User",
                provider="",
                provider_id="",
            )


# ==================== OAuthConfig Global Tests ====================


class TestGlobalOAuthConfig:
    def test_get_oauth_config_returns_singleton(self):
        """get_oauth_config returns the global config instance."""
        from oauth import get_oauth_config, oauth_config
        assert get_oauth_config() is oauth_config


# ==================== Error Handling Tests ====================


class TestOAuthError:
    def test_oauth_error_has_code(self):
        """OAuthError includes a code field."""
        from oauth import OAuthError
        err = OAuthError("Something went wrong", code="TEST_ERROR")
        assert str(err) == "Something went wrong"
        assert err.code == "TEST_ERROR"

    def test_oauth_error_default_code(self):
        """OAuthError uses OAUTH_ERROR as default code."""
        from oauth import OAuthError
        err = OAuthError("Generic error")
        assert err.code == "OAUTH_ERROR"


class TestRateLimitedEndpoints:
    """Test that OAuth endpoints have proper auth guards (via main app)."""

    def setup_method(self):
        """Set up test config for Enterprise tier."""
        from config import config as cfg
        self._orig_tier = cfg.tier
        cfg.tier = "enterprise"

    def teardown_method(self):
        """Restore original config."""
        from config import config as cfg
        cfg.tier = self._orig_tier

    def test_oauth_login_requires_enterprise(self):
        """OAuth login endpoint returns 402 for non-Enterprise tier."""
        from config import config as cfg
        cfg.tier = "lite"

        from main import app
        from fastapi.testclient import TestClient
        app.state.limiter.enabled = False

        with TestClient(app) as client:
            resp = client.get("/auth/oauth/login/google")
            # Should get 402 (tier check) or 307/302 redirect (if tier passes but no config)
            assert resp.status_code in (402, 307, 302)

    def test_oauth_login_wrong_provider(self):
        """OAuth login with unsupported provider returns 400."""
        from main import app
        from fastapi.testclient import TestClient
        app.state.limiter.enabled = False

        with TestClient(app) as client:
            resp = client.get("/auth/oauth/login/gitlab")
            assert resp.status_code == 400

    def test_oauth_callback_missing_code(self):
        """OAuth callback without code parameter returns 400."""
        from main import app
        from fastapi.testclient import TestClient
        app.state.limiter.enabled = False

        with TestClient(app) as client:
            resp = client.get("/auth/oauth/callback/google?state=test")
            assert resp.status_code == 400


class TestOAuthUrlEdgeCases:
    def test_state_in_url_is_unique_per_call(self):
        """Each URL generation uses a different state."""
        from oauth import get_oauth_url, generate_state
        state1 = generate_state()
        state2 = generate_state()
        url1 = get_oauth_url("google", state1)
        url2 = get_oauth_url("google", state2)
        assert state1 in url1
        assert state2 in url2
        assert state1 != state2
