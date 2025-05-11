import logging
from django.core.management.base import BaseCommand

from pages.models import Content

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalize content"

    def handle(self, *args, **options):
        log.info("counting content objects...")
        count = Content.objects.count()
        log.info(f"found {count} Content objects.")
        contents = Content.objects.order_by("id").all()
        for i, content in enumerate(contents.iterator(), start=1):
            log.info(f"normalizing {content} ...")
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
            log.info(f"{content} normalized. {i}/{count} ({i/count*100:.2f}%)")
