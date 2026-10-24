from django.core.management.base import BaseCommand

from apps.accounts.views import DEMO_UID
from apps.analysis.parser import normalise
from apps.analysis.service import shop_and_fit
from apps.core.testing import SAMPLE_REPLY
from apps.dashboard.services import invalidate_dashboard
from apps.storage import get_repository


def _no_search(query, gl):
    return []


class Command(BaseCommand):
    help = "Give the demo account a sample style plan (offline backup for presentations)."

    def add_arguments(self, parser):
        parser.add_argument("--gender", choices=["men", "women"], default="men")
        parser.add_argument("--live", action="store_true",
                            help="Look up real images, links and prices with SERPER_API_KEY")

    def handle(self, *args, **options):
        repo = get_repository()
        profile = {
            "gender": options["gender"], "age": 22, "budget": 3000, "currency": "MAD",
            "country": "ma", "city": "Rabat",
        }
        analysis, products = normalise(SAMPLE_REPLY, "MAD")
        analysis, products = shop_and_fit(analysis, products, profile, None if options["live"] else _no_search)
        repo.save_user(DEMO_UID, {
            "display_name": "Demo User", "email": "demo@mraya.local", **profile,
            "has_analysis": True, "profile_xp_awarded": True,
        })
        repo.add_analysis(DEMO_UID, analysis, products)
        repo.increment_xp(DEMO_UID, 150)
        invalidate_dashboard(DEMO_UID)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(products)} products for {DEMO_UID}"))
