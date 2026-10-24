"""Prompt construction for the Gemma stylist."""
import json

from .budget import category_allowances

CATEGORIES = {
    "clothing": "Clothing",
    "hair": "Hair products",
    "skincare": "Skincare routine",
    "perfume": "Perfume",
    "shoes": "Shoes",
    "accessories": "Accessories",
}

RESPONSE_SCHEMA = {
    "summary": "2-3 warm, specific sentences about the person's current look and the plan",
    "style_profile": {
        "body_type": "short description",
        "face_shape": "short description",
        "skin_tone": "short description (undertone, type if visible)",
        "hair": "short description of current hair",
        "style_archetype": "e.g. smart casual, streetwear, classic",
    },
    "style_score": "integer 0-100 for the current look (be honest but encouraging)",
    "routine": {
        "morning": ["step", "..."],
        "evening": ["step", "..."],
    },
    "categories": [
        {
            "category": "one of: " + ", ".join(CATEGORIES),
            "advice": "1-2 sentences of advice for this category",
            "products": [
                {
                    "name": "specific product name",
                    "brand": "brand",
                    "search_query": "brand + exact product name + size, as you would type it in a shop search",
                    "priority": "essential or nice",
                    "price": "number, estimated price",
                    "currency": "currency code",
                    "where_to_buy": "store or website, ideally near the user's city",
                    "why": "one sentence: why it suits this person",
                }
            ],
        }
    ],
}


def build_prompt(profile):
    interests = [c for c in profile.get("interests") or CATEGORIES if c in CATEGORIES]
    gender_word = {"men": "man", "women": "woman"}.get(profile.get("gender"), "person")
    brands = profile.get("brand_preferences", "").strip()
    if brands:
        brand_rule = f"Prefer these brands when they fit: {brands}."
        if profile.get("suggest_brands"):
            brand_rule += " You may also suggest other brands that suit them."
    else:
        brand_rule = "The user has no brand preference: recommend well-known, reliable brands that fit the budget."

    allowances = category_allowances(float(profile.get("budget") or 0), interests)
    currency = profile.get("currency")
    budget_lines = "\n".join(f"  - {cat}: up to {amount:g} {currency}" for cat, amount in allowances.items())

    return f"""You are Mraya, an expert personal stylist, groomer and skincare advisor.
You receive two photos: IMAGE 1 is a full-body photo, IMAGE 2 is a close-up of the face.
Study body proportions, posture, current outfit and colours (image 1), and face shape,
skin tone and visible skin condition, and hair (image 2).

User profile:
- Gender: {gender_word}
- Age: {profile.get("age")}
- Total budget for all products: {profile.get("budget")} {profile.get("currency")}
- City / country: {profile.get("city") or "not given"}
- Style preferences: {profile.get("style_preferences") or "not given"}
- {brand_rule}

Rules:
- Only cover these categories, in this order: {", ".join(interests)}.
- Give 2 or 3 products per category. Budget per category:
{budget_lines}
- Each category's products together must stay within its budget. Mark the one product
  per category the person needs most as "essential", the others as "nice".
- Use the currency {profile.get("currency")} for every price.
- "where_to_buy" should name real stores or websites available in the user's city/country when given.
- Skincare must be gentle and non-medical; never diagnose conditions.
- Be respectful and body-positive. Never comment on weight negatively.

Reply with ONLY one JSON object, no markdown, matching this shape:
{json.dumps(RESPONSE_SCHEMA, indent=2)}
"""


RETRY_SUFFIX = (
    "\n\nIMPORTANT: your previous reply was not valid JSON. "
    "Reply again with ONLY the JSON object, starting with '{' and ending with '}'."
)
