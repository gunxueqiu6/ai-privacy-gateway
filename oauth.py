"""
OAuth 2.0 integration module for AI Privacy Gateway.
Supports Google and GitHub as identity providers.
"""
import logging
import os
import secrets
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# Provider configuration maps
PROVIDER_CONFIGS: Dict[str, Dict[str, str]] = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": "openid email profile",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": "read:user user:email",
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
    },
}

SUPPORTED_PROVIDERS = frozenset(PROVIDER_CONFIGS.keys())


class OAuthError(Exception):
    """Raised when OAuth operations fail."""

    def __init__(self, message: str, code: str = "OAUTH_ERROR") -> None:
        super().__init__(message)
        self.code = code


class OAuthConfig:
    """OAuth configuration read from environment variables."""

    def __init__(self) -> None:
        self.google_client_id: str = os.environ.get("GOOGLE_CLIENT_ID", "")
        self.google_client_secret: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
        self.github_client_id: str = os.environ.get("GITHUB_CLIENT_ID", "")
        self.github_client_secret: str = os.environ.get("GITHUB_CLIENT_SECRET", "")
        self.redirect_base: str = os.environ.get(
            "OAUTH_REDIRECT_BASE", "http://localhost:9999"
        )

    def is_provider_configured(self, provider: str) -> bool:
        """Check if a provider has client ID and secret set."""
        cfg = PROVIDER_CONFIGS.get(provider)
        if not cfg:
            return False
        client_id = getattr(self, f"{provider}_client_id", "")
        client_secret = getattr(self, f"{provider}_client_secret", "")
        return bool(client_id and client_secret)

    def get_configured_providers(self) -> list[str]:
        """Return list of providers with valid configuration."""
        return [p for p in SUPPORTED_PROVIDERS if self.is_provider_configured(p)]


# Global config instance
oauth_config = OAuthConfig()


def get_oauth_config() -> OAuthConfig:
    """Get the global OAuth config instance."""
    return oauth_config


def _get_provider_cfg(provider: str) -> Dict[str, str]:
    """Get the provider config dict, raising OAuthError if unknown."""
    cfg = PROVIDER_CONFIGS.get(provider)
    if not cfg:
        raise OAuthError(
            f"Unsupported OAuth provider: {provider}. Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}",
            code="UNSUPPORTED_PROVIDER",
        )
    return cfg


def _get_client_credentials(provider: str) -> tuple[str, str]:
    """Get client_id and client_secret for a provider."""
    cfg = _get_provider_cfg(provider)
    client_id = getattr(oauth_config, f"{provider}_client_id", "")
    client_secret = getattr(oauth_config, f"{provider}_client_secret", "")

    if not client_id or not client_secret:
        raise OAuthError(
            f"OAuth provider '{provider}' is not configured. "
            f"Set {cfg['client_id_env']} and {cfg['client_secret_env']} environment variables.",
            code="PROVIDER_NOT_CONFIGURED",
        )

    return client_id, client_secret


def generate_state() -> str:
    """Generate a random state string for CSRF protection."""
    return secrets.token_urlsafe(32)


def get_oauth_url(provider: str, state: str) -> str:
    """Generate the OAuth authorization URL for the given provider.

    Args:
        provider: "google" or "github"
        state: A random state string for CSRF protection.

    Returns:
        The full authorization URL to redirect the user to.

    Raises:
        OAuthError: If the provider is unknown or not configured.
    """
    cfg = _get_provider_cfg(provider)
    client_id, _ = _get_client_credentials(provider)

    redirect_uri = f"{oauth_config.redirect_base}/auth/oauth/callback/{provider}"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg["scopes"],
        "state": state,
        "access_type": "offline" if provider == "google" else None,
        "prompt": "consent" if provider == "google" else None,
    }

    # Remove None values
    query_params = {k: v for k, v in params.items() if v is not None}

    url = f"{cfg['authorize_url']}?{urlencode(query_params)}"
    logger.info("Generated OAuth URL for provider=%s", provider)
    return url


async def exchange_code(provider: str, code: str) -> Dict[str, Any]:
    """Exchange an authorization code for user info.

    Args:
        provider: "google" or "github"
        code: The authorization code from the OAuth callback.

    Returns:
        A dict with keys: email, name, provider, provider_id

    Raises:
        OAuthError: If token exchange or user info retrieval fails.
    """
    cfg = _get_provider_cfg(provider)
    client_id, client_secret = _get_client_credentials(provider)

    redirect_uri = f"{oauth_config.redirect_base}/auth/oauth/callback/{provider}"

    # Exchange code for token
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    token_headers = {"Accept": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            token_resp = await client.post(
                cfg["token_url"],
                data=token_data,
                headers=token_headers,
            )
            token_resp.raise_for_status()
            token_json = token_resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Token exchange failed for %s: HTTP %d - %s",
                provider,
                e.response.status_code,
                e.response.text,
            )
            raise OAuthError(
                f"Token exchange failed: HTTP {e.response.status_code}",
                code="TOKEN_EXCHANGE_FAILED",
            )
        except httpx.RequestError as e:
            logger.error("Token exchange request failed for %s: %s", provider, str(e))
            raise OAuthError(
                f"Token exchange request failed: {str(e)}",
                code="TOKEN_EXCHANGE_FAILED",
            )

    access_token = token_json.get("access_token")
    if not access_token:
        logger.error(
            "No access_token in response for %s: %s", provider, token_json
        )
        raise OAuthError(
            "No access_token in provider response",
            code="NO_ACCESS_TOKEN",
        )

    # Fetch user info with the access token
    userinfo_headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            user_resp = await client.get(
                cfg["userinfo_url"],
                headers=userinfo_headers,
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "User info fetch failed for %s: HTTP %d - %s",
                provider,
                e.response.status_code,
                e.response.text,
            )
            raise OAuthError(
                f"Failed to fetch user info: HTTP {e.response.status_code}",
                code="USERINFO_FETCH_FAILED",
            )
        except httpx.RequestError as e:
            logger.error(
                "User info request failed for %s: %s", provider, str(e)
            )
            raise OAuthError(
                f"Failed to fetch user info: {str(e)}",
                code="USERINFO_FETCH_FAILED",
            )

    # Extract user info
    if provider == "google":
        user_info = {
            "email": user_data.get("email", ""),
            "name": user_data.get("name", user_data.get("email", "")),
            "provider": provider,
            "provider_id": user_data.get("id", ""),
        }
    elif provider == "github":
        # GitHub may not include email; fetch emails separately if needed
        email = user_data.get("email", "")
        # If email is not in primary response, try to get it from emails endpoint
        if not email:
            email = await _fetch_github_primary_email(access_token)

        user_info = {
            "email": email or f"{user_data.get('login', 'unknown')}@github.oauth",
            "name": user_data.get("name") or user_data.get("login", email),
            "provider": provider,
            "provider_id": str(user_data.get("id", "")),
        }
    else:
        raise OAuthError(f"Unsupported provider: {provider}", code="UNSUPPORTED_PROVIDER")

    if not user_info.get("provider_id"):
        raise OAuthError(
            "Could not determine user identity from provider",
            code="MISSING_PROVIDER_ID",
        )

    logger.info(
        "OAuth exchange successful for provider=%s, email=%s",
        provider,
        user_info.get("email"),
    )
    return user_info


async def _fetch_github_primary_email(access_token: str) -> str:
    """Fetch the primary email from GitHub's emails endpoint."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.github.com/user/emails",
                headers=headers,
            )
            resp.raise_for_status()
            emails = resp.json()
            for email_entry in emails:
                if email_entry.get("primary") and email_entry.get("verified"):
                    return email_entry["email"]
            # Fall back to first verified email
            for email_entry in emails:
                if email_entry.get("verified"):
                    return email_entry["email"]
            return emails[0]["email"] if emails else ""
    except (httpx.HTTPStatusError, httpx.RequestError, IndexError, KeyError) as e:
        logger.warning("Failed to fetch GitHub primary email: %s", str(e))
        return ""
