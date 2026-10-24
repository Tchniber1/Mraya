"""High-level entry point: profile + photos -> normalised analysis and products."""
import logging

from . import gemma_client, shopping
from .budget import category_allowances, fit_to_budget
from .parser import AnalysisParseError, extract_json, normalise
from .prompts import RETRY_SUFFIX, build_prompt

logger = logging.getLogger("apps.analysis")


class AnalysisFailed(RuntimeError):
    pass


def shop_and_fit(analysis, products, profile, fetch):
    currency = profile.get("currency", "MAD")
    budget = float(profile.get("budget") or 0)
    allowances = category_allowances(budget, [c["category"] for c in analysis["categories"]])
    products = shopping.enrich(products, currency, allowances, profile.get("country") or "ma", fetch=fetch)
    products, analysis["budget"] = fit_to_budget(products, budget, currency)
    return analysis, products


def run_analysis(profile, full_body_jpeg, face_jpeg, client=None, fetch=None):
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
            analysis, products = normalise(extract_json(text), profile.get("currency", "MAD"))
            return shop_and_fit(analysis, products, profile, fetch)
        except AnalysisParseError as exc:
            logger.warning("Gemma reply unusable (attempt %s): %s", attempt + 1, exc)
            last_error = exc
        except gemma_client.GemmaUnavailable as exc:
            raise AnalysisFailed("The AI stylist is unreachable right now. Please try again.") from exc
    raise AnalysisFailed("The AI stylist sent an unexpected answer. Please try again.") from last_error
