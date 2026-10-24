"""Shared test helpers: isolated local store, signed-in client, fake images, fake Gemma."""
import io
import json
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from PIL import Image

from apps.storage import get_repository

SAMPLE_REPLY = {
    "summary": "Clean, balanced look with room for sharper fits.",
    "style_profile": {"body_type": "athletic", "face_shape": "oval", "skin_tone": "warm olive",
                      "hair": "short wavy", "style_archetype": "smart casual"},
    "style_score": 72,
    "routine": {"morning": ["Cleanser", "SPF 50"], "evening": ["Cleanser", "Moisturiser"]},
    "categories": [
        {"category": "clothing", "advice": "Go slim, not skinny.",
         "products": [{"name": "Oxford shirt", "brand": "Zara", "price": 299, "currency": "MAD",
                       "where_to_buy": "Zara Morocco Mall", "why": "Sharpens your shoulders."}]},
        {"category": "Fragrance", "advice": "Fresh woody notes.",
         "products": [{"name": "Bleu EDT", "brand": "Chanel", "price": "1,200 MAD",
                       "where_to_buy": "Sephora", "why": "Versatile."}]},
    ],
}


def image_bytes(size=(60, 90), fmt="JPEG", color=(180, 120, 90)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


class FakeGemma:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def generate(self, prompt, images=()):
        self.calls.append((prompt, len(images)))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)


class MrayaTestCase(TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._override = override_settings(
            MRAYA_STORAGE="local", MRAYA_LOCAL_STORE_PATH=Path(self._tmp) / "store.json",
            SERPER_API_KEY="",  # never spend real searches in tests
        )
        self._override.enable()
        get_repository.cache_clear()
        cache.clear()
        self.repo = get_repository()

    def tearDown(self):
        self._override.disable()
        get_repository.cache_clear()
        shutil.rmtree(self._tmp, ignore_errors=True)

    def sign_in(self, uid="u1", name="Taha Test"):
        session = self.client.session
        session["mraya_user"] = {"uid": uid, "email": "t@example.com", "name": name, "picture": ""}
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return uid
