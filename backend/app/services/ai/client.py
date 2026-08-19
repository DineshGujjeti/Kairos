"""Gemini API client using google-genai SDK with production-grade error handling."""
import time
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from google import genai
    from google.genai import errors as genai_errors
    from google.genai.types import GenerateContentConfig
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiClient:
    """Production-grade Gemini API client using google-genai SDK."""

    def __init__(self):
        self.available = False
        self.client = None
        self.model_name = settings.GEMINI_MODEL
        self.request_count = 0
        self.error_count = 0

        if not GENAI_AVAILABLE:
            logger.info("gemini_not_configured", reason="google-genai SDK not installed")
            return

        if not settings.GEMINI_API_KEY:
            logger.info("gemini_not_configured", reason="GEMINI_API_KEY not set")
            return

        try:
            # Initialize using the official google-genai SDK.
            # Pass api_key directly to Client() — no global configure() call needed.
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

            # Mark as available immediately — the API key and SDK are present.
            # We do NOT call models.list() here: that adds a round-trip on every
            # startup, fails in restricted network environments, and errors would
            # only tell us that *listing* failed, not that *generation* will fail.
            # Real errors (bad key, unknown model, quota) are surfaced at call time
            # with proper classification in _classify_error().
            self.available = True
            logger.info("gemini_initialized", model=self.model_name)

        except Exception as e:
            self.available = False
            logger.warning("gemini_init_failed", error=str(e), error_type=type(e).__name__)

    def is_available(self) -> bool:
        """Check if Gemini is properly configured and available."""
        return self.available and self.client is not None

    def _classify_error(self, error: Exception) -> tuple[bool, str]:
        """
        Classify an error as retryable or not.
        Returns (is_retryable, error_message).

        Non-retryable: 400, 401, 403, 404 — permanent failures.
        Retryable: 429, 500, 503 — transient failures.
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Use structured error codes when available (google.genai.errors)
        code = getattr(error, "code", None)

        if code is not None:
            if code in (400, 401, 403, 404):
                labels = {
                    400: "Bad request",
                    401: "Authentication failed",
                    403: "Permission denied / host not in allowlist",
                    404: "Model not found",
                }
                return False, labels.get(code, f"Client error ({code})")
            if code in (429, 500, 503):
                labels = {
                    429: "Rate limit exceeded (429)",
                    500: "Internal server error (500)",
                    503: "Service unavailable (503)",
                }
                return True, labels.get(code, f"Server error ({code})")

        # Fall back to string matching for unknown error types
        if "404" in error_str or "not found" in error_str:
            return False, "Model not found (404)"
        if "authentication" in error_str or "invalid api key" in error_str or "unauthorized" in error_str:
            return False, "Authentication failed"
        if "permission" in error_str or "forbidden" in error_str:
            return False, "Permission denied"
        if "invalid" in error_str and ("model" in error_str or "parameter" in error_str):
            return False, "Invalid model or parameter"
        if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
            return True, "Rate limit exceeded (429)"
        if "503" in error_str or "service unavailable" in error_str:
            return True, "Service unavailable (503)"
        if "500" in error_str or "internal error" in error_str:
            return True, "Internal server error (500)"
        if "timeout" in error_str or "timed out" in error_str:
            return True, "Request timeout"
        if "connection" in error_str or "network" in error_str:
            return True, "Network error"

        return False, f"SDK error: {error_type}: {str(error)[:120]}"

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> tuple[str, dict]:
        """
        Generate content using Gemini with intelligent retry logic.
        Returns (response_text, error_info).
        error_info is {} on success, or a dict with error details on failure.
        """
        if not self.is_available():
            return "", {"error": "Gemini not configured", "retryable": False}

        for attempt in range(settings.GEMINI_MAX_RETRIES):
            try:
                config = GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    system_instruction=system_instruction,
                )

                # model_name is read from settings — never hardcoded.
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )

                self.request_count += 1

                if response.text:
                    return response.text, {}
                else:
                    return "", {"error": "Empty response from Gemini", "retryable": False}

            except Exception as e:
                is_retryable, error_msg = self._classify_error(e)
                self.error_count += 1

                logger.warning(
                    "gemini_request_failed",
                    attempt=attempt + 1,
                    max_retries=settings.GEMINI_MAX_RETRIES,
                    error=error_msg,
                    retryable=is_retryable,
                )

                if is_retryable and attempt < settings.GEMINI_MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue

                return "", {
                    "error": error_msg,
                    "retryable": is_retryable,
                    "attempt": attempt + 1,
                }

        return "", {
            "error": "Max retries exceeded",
            "retryable": False,
            "attempt": settings.GEMINI_MAX_RETRIES,
        }

    def count_tokens(self, text: str) -> int:
        """Count tokens in text. Falls back to character-based estimate."""
        if not self.is_available():
            return max(1, len(text) // 4)

        try:
            response = self.client.models.count_tokens(
                model=self.model_name,
                contents=text,
            )
            return response.total_tokens if hasattr(response, "total_tokens") else len(text) // 4
        except Exception as e:
            logger.warning("token_count_failed", error=str(e))
            return len(text) // 4

    def get_status(self) -> dict:
        """Get detailed status of Gemini integration."""
        return {
            "available": self.available,
            "configured": bool(settings.GEMINI_API_KEY),
            "model": self.model_name,
            "sdk": "google-genai",
            "request_count": self.request_count,
            "error_count": self.error_count,
            "max_retries": settings.GEMINI_MAX_RETRIES,
            "timeout_seconds": settings.GEMINI_TIMEOUT,
        }


# Singleton — reset to None allows tests to re-initialise with different settings
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get or create the singleton Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


def reset_gemini_client() -> None:
    """Reset singleton — used in tests."""
    global _gemini_client
    _gemini_client = None
