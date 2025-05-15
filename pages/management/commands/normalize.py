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
            if not content.block_time:
                content.block_time = content.block.time
            if not content.block_height:
                content.block_height = content.block.blockheight
            if content.inscription is not None:
                text = content.inscription.text
                if isinstance(content.inscription.json, dict):
                    is_brc20 = (
                        True if content.inscription.json.get("p") == "brc-20" else False
                    )
                else:
                    is_brc20 = False
            elif content.coinbase_scriptsig is not None:
                text = content.coinbase_scriptsig.scriptsig_text
                is_brc20 = False
            elif content.op_return is not None:
                text = content.op_return.scriptpubkey_text
                is_brc20 = False
            if text is None:
                text = ""
            content.text = text
            if content.is_brc20 is None:
                content.is_brc20 = is_brc20
            if "/" in content.mime_type:
                content.mime_type, content.mime_subtype = content.mime_type.split("/")
            content.save()
            log.info(f"{content} normalized. {i}/{count} ({i/count*100:.2f}%)")
            # del content
