"""Gemma 4 through the Gemini API (google-genai SDK)."""
import logging

from django.conf import settings

logger = logging.getLogger("apps.analysis")


class GemmaUnavailable(RuntimeError):
    pass


class GemmaClient:
    def __init__(self, api_key=None, model=None, timeout_ms=None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMMA_MODEL
        self.timeout_ms = timeout_ms or settings.GEMMA_TIMEOUT_MS
        if not self.api_key:
            raise GemmaUnavailable("GEMINI_API_KEY is not set")
        from google import genai
        from google.genai import types

        self._types = types
        self._client = genai.Client(
            api_key=self.api_key, http_options=types.HttpOptions(timeout=self.timeout_ms)
        )

    def generate(self, prompt, images=()):
        """Send JPEG ``images`` (bytes) followed by ``prompt``; return the reply text."""
        types = self._types
        parts = [types.Part.from_bytes(data=img, mime_type="image/jpeg") for img in images]
        parts.append(types.Part.from_text(text=prompt))
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(temperature=0.7),
            )
        except Exception as exc:
            logger.exception("Gemma request failed")
            raise GemmaUnavailable(str(exc)) from exc
        return response.text or ""


def get_client():
    return GemmaClient()
