"""Real product data (image, link, store, price) from Google Shopping via Serper.dev.

Each product is searched in the user's country first, then abroad. Any failure falls
back to Gemma's estimate and a Google Shopping search link, so enrichment never
makes an analysis fail.
"""
import json
import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus, urlparse

from django.conf import settings

from .countries import abroad_countries
from .currency import convert, parse_price

logger = logging.getLogger("apps.analysis")

SERPER_URL = "https://google.serper.dev/shopping"
TIMEOUT_SECONDS = 6
MAX_WORKERS = 8


def search_url(query):
    return f"https://www.google.com/search?tbm=shop&q={quote_plus(query)}"


def serper_fetch(query, gl):
    request = urllib.request.Request(
        SERPER_URL,
        data=json.dumps({"q": query, "gl": gl}).encode("utf-8"),
        headers={"X-API-KEY": settings.SERPER_API_KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response).get("shopping") or []


def _price_in(result, currency):
    """``(price in currency, converted?)`` or ``(None, False)``."""
    amount, code = parse_price(result.get("price"))
    if amount is None:
        return None, False
    if code in (None, currency):
        return amount, False
    converted = convert(amount, code, currency)
    return (converted, True) if converted is not None else (None, False)


def _is_web_url(value):
    """Only http(s) URLs reach an href/src; blocks javascript:, data: and friends."""
    return isinstance(value, str) and urlparse(value).scheme in ("http", "https")


def pick_result(results, allowance, currency):
    """First result with image + link within ``allowance``; else the cheapest such result."""
    candidates = [r for r in results if _is_web_url(r.get("imageUrl")) and _is_web_url(r.get("link"))]
    priced = [(r, _price_in(r, currency)[0]) for r in candidates]
    priced = [(r, price) for r, price in priced if price is not None]
    if allowance is not None:
        for result, price in priced:
            if price <= allowance:
                return result
    if priced:
        return min(priced, key=lambda pair: pair[1])[0]
    return candidates[0] if candidates else None


def _fallback(product, country):
    return {**product, "image_url": "", "link": search_url(product["search_query"]), "store": "",
            "price_source": "estimate", "price_converted": False, "origin": "local", "origin_country": country}


def _enrich_one(product, currency, allowance, country, fetch):
    for gl in [country, *abroad_countries(country)]:
        try:
            result = pick_result(fetch(product["search_query"], gl), allowance, currency)
        except Exception as exc:  # network, quota, bad JSON...
            logger.warning("Shopping search failed for %r (%s): %s", product["search_query"], gl, exc)
            return _fallback(product, country)
        if result is None:
            continue
        price, converted = _price_in(result, currency)
        return {
            **product,
            "image_url": result["imageUrl"],
            "link": result["link"],
            "store": str(result.get("source") or "")[:80],
            "price": price if price is not None else product.get("price"),
            "currency": currency,
            "price_source": "store" if price is not None else "estimate",
            "price_converted": converted,
            "origin": "local" if gl == country else "abroad",
            "origin_country": gl,
        }
    return _fallback(product, country)


def enrich(products, currency, allowances, country="ma", fetch=None):
    if fetch is None:
        if not settings.SERPER_API_KEY:
            return [_fallback(p, country) for p in products]
        fetch = serper_fetch
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        return list(pool.map(
            lambda p: _enrich_one(p, currency, allowances.get(p["category"]), country, fetch), products
        ))
