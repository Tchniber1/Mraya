from django.core.management.base import BaseCommand, CommandError

from apps.analysis.gemma_client import GemmaClient, GemmaUnavailable


class Command(BaseCommand):
    help = "Smoke-test the Gemma 4 connection through the Gemini API."

    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true", help="List the Gemma models available to this key")

    def handle(self, *args, **options):
        try:
            client = GemmaClient()
        except GemmaUnavailable as exc:
            raise CommandError(str(exc)) from exc

        if options["list"]:
            for model in client._client.models.list():
                if "gemma" in model.name:
                    self.stdout.write(model.name)
            return

        self.stdout.write(f"Calling {client.model} ...")
        try:
            reply = client.generate('Reply with exactly: {"ok": true}')
        except GemmaUnavailable as exc:
            raise CommandError(f"Gemma call failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Gemma replied: {reply.strip()[:200]}"))
