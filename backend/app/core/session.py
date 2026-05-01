"""OAuth state management using signed cookies for CSRF protection."""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import Settings


class StateManager:
    """Manages OAuth state parameters using signed tokens.

    State tokens are signed with the application secret key and have a
    configurable expiration time to prevent replay attacks.
    """

    # State tokens expire after 10 minutes (OAuth flow should complete quickly)
    STATE_MAX_AGE_SECONDS = 600

    def __init__(self, settings: Settings) -> None:
        """Initialize state manager with settings.

        Args:
            settings: Application settings containing secret_key
        """
        self.serializer = URLSafeTimedSerializer(settings.secret_key)
        self._settings = settings

    def sign_state(self, state: str, provider: str = "google") -> str:
        """Create a signed token containing the state and provider.

        Args:
            state: The OAuth state parameter to sign
            provider: The OAuth provider ("google" or "microsoft")

        Returns:
            Signed token that can be stored in a cookie
        """
        payload = {"state": state, "provider": provider}
        signed: str = self.serializer.dumps(payload)
        return signed

    def verify_state(self, signed_state: str) -> str | None:
        """Verify a signed state token and extract the original state.

        Args:
            signed_state: The signed token from the cookie

        Returns:
            The original state value if valid, None otherwise
        """
        try:
            data = self.serializer.loads(signed_state, max_age=self.STATE_MAX_AGE_SECONDS)
            if isinstance(data, dict):
                state: str = data["state"]
                return state
            # Backwards compatibility with plain string state
            return str(data)
        except (BadSignature, SignatureExpired):
            return None

    def verify_state_with_provider(self, signed_state: str) -> tuple[str | None, str]:
        """Verify a signed state token and extract state and provider.

        Args:
            signed_state: The signed token from the cookie

        Returns:
            Tuple of (state, provider). State is None if invalid.
        """
        try:
            data = self.serializer.loads(signed_state, max_age=self.STATE_MAX_AGE_SECONDS)
            if isinstance(data, dict):
                return data["state"], data.get("provider", "google")
            return str(data), "google"
        except (BadSignature, SignatureExpired):
            return None, "google"

    def validate_state(self, signed_state: str | None, request_state: str) -> bool:
        """Validate that the request state matches the signed state.

        Args:
            signed_state: The signed token from the cookie (may be None)
            request_state: The state parameter from the OAuth callback

        Returns:
            True if states match, False otherwise
        """
        if signed_state is None:
            return False

        expected_state = self.verify_state(signed_state)
        if expected_state is None:
            return False

        return expected_state == request_state


def get_state_manager(settings: Settings) -> StateManager:
    """Factory function to create a StateManager.

    Args:
        settings: Application settings

    Returns:
        Configured StateManager instance
    """
    return StateManager(settings)
