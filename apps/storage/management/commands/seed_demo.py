from django.core.management.base import BaseCommand

from apps.accounts.views import DEMO_UID
from apps.analysis.parser import normalise
from apps.core.testing import SAMPLE_REPLY
from apps.dashboard.services import invalidate_dashboard
from apps.storage import get_repository


class Command(BaseCommand):
    help = "Give the demo account a sample style plan (offline backup for presentations)."

    def add_arguments(self, parser):
        parser.add_argument("--gender", choices=["men", "women"], default="men")

    def handle(self, *args, **options):
        repo = get_repository()
        analysis, products = normalise(SAMPLE_REPLY, "MAD")
        repo.save_user(DEMO_UID, {
            "display_name": "Demo User", "email": "demo@mraya.local", "gender": options["gender"],
            "age": 22, "budget": 3000, "currency": "MAD", "city": "Rabat",
            "has_analysis": True, "profile_xp_awarded": True,
        })
        repo.add_analysis(DEMO_UID, analysis, products)
        repo.increment_xp(DEMO_UID, 150)
        invalidate_dashboard(DEMO_UID)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(products)} products for {DEMO_UID}"))
