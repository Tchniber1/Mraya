"""Splitting the budget across categories and trimming products to fit it (pure, no I/O)."""

CATEGORY_WEIGHTS = {"clothing": 35, "shoes": 20, "perfume": 15, "skincare": 12, "hair": 10, "accessories": 8}


def category_allowances(budget, categories):
    """Share of ``budget`` per category, re-normalised to the chosen ones; sums to ``budget``."""
    chosen = [c for c in categories if c in CATEGORY_WEIGHTS]
    if not chosen:
        return {}
    total_weight = sum(CATEGORY_WEIGHTS[c] for c in chosen)
    shares = {c: round(budget * CATEGORY_WEIGHTS[c] / total_weight, 2) for c in chosen[:-1]}
    shares[chosen[-1]] = round(budget - sum(shares.values()), 2)
    return shares


def _number(value):
    return int(value) if float(value).is_integer() else round(value, 2)


def fit_to_budget(products, limit, currency):
    """Keep the products that fit ``limit``: one per category first, then essentials, then the rest.

    Products without a price are kept but not counted. Returns ``(kept, summary)``.
    """
    priced = [i for i, p in enumerate(products) if p.get("price") is not None]
    chosen, used = set(), 0.0

    def take(index):
        nonlocal used
        price = products[index]["price"]
        if used + price <= limit + 1e-9:
            chosen.add(index)
            used += price

    cheapest = {}
    for i in priced:
        cat = products[i]["category"]
        if cat not in cheapest or products[i]["price"] < products[cheapest[cat]]["price"]:
            cheapest[cat] = i
    for i in sorted(cheapest.values(), key=lambda i: products[i]["price"]):
        take(i)

    rest = [i for i in priced if i not in chosen]
    for i in sorted(rest, key=lambda i: (products[i].get("priority") != "essential", products[i]["price"])):
        take(i)

    kept = [p for i, p in enumerate(products) if i in chosen or p.get("price") is None]
    summary = {"limit": _number(limit), "used": _number(round(used, 2)), "currency": currency,
               "dropped": len(priced) - len(chosen)}
    return kept, summary
