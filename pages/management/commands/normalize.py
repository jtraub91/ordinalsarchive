import logging
from django.core.management.base import BaseCommand

from pages.models import Content

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalize content"

    def handle(self, *args, **options):
        count = Content.objects.count()
        for i, content in enumerate(Content.objects.all()):
            content.block_time = content.block.time
            if content.inscription is not None:
                text = content.inscription.text
            elif content.coinbase_scriptsig is not None:
                text = content.coinbase_scriptsig.scriptsig_text
            elif content.op_return is not None:
                text = content.op_return.scriptpubkey_text
            if text is None:
                text = ""
            content.text = text
            content.save()
            log.info(f"{content} normalized. {i+1}/{count} ({(i+1)/count*100:.2f}%)")
