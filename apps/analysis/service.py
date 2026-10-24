"""High-level entry point: profile + photos -> normalised analysis and products."""
import logging

from . import gemma_client
from .parser import AnalysisParseError, extract_json, normalise
from .prompts import RETRY_SUFFIX, build_prompt

logger = logging.getLogger("apps.analysis")


class AnalysisFailed(RuntimeError):
    pass


def run_analysis(profile, full_body_jpeg, face_jpeg, client=None):
    try:
        client = client or gemma_client.get_client()
    except gemma_client.GemmaUnavailable as exc:
        raise AnalysisFailed("The AI stylist is not configured yet (missing Gemini API key).") from exc

    prompt = build_prompt(profile)
    images = (full_body_jpeg, face_jpeg)
    last_error = None
    for attempt in range(2):
        try:
            text = client.generate(prompt if attempt == 0 else prompt + RETRY_SUFFIX, images)
            return normalise(extract_json(text), profile.get("currency", "MAD"))
        except AnalysisParseError as exc:
            logger.warning("Gemma reply unusable (attempt %s): %s", attempt + 1, exc)
            last_error = exc
        except gemma_client.GemmaUnavailable as exc:
            raise AnalysisFailed("The AI stylist is unreachable right now. Please try again.") from exc
    raise AnalysisFailed("The AI stylist sent an unexpected answer. Please try again.") from last_error
