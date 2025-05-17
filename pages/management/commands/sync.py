import logging
import time

import requests
from django.core.management.base import BaseCommand
from django.core.management import call_command

from pages.models import Block


log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync with blockchain"

    def handle(self, *args, **options):
        while True:
            latest_block = Block.objects.order_by("-blockheight").first()
            log.info(f"Latest blockheight in db: {latest_block.blockheight}")
            try:
                req = requests.get(f"https://mempool.space/api/blocks/tip/height")
                tip = int(req.text)
                log.info(f"Tip blockheight per mempool.space: {tip}")
            except Exception as e:
                log.error(f"Failed to get tip blockheight: {e}")
                time.sleep(60)
                continue
            if latest_block.blockheight < tip:
                log.info(f"Indexing block {latest_block.blockheight + 1}...")
                try:
                    call_command(
                        "index", latest_block.blockheight + 1, reupload_s3=True
                    )
                except Exception as e:
                    log.error(
                        f"Failed to index block {latest_block.blockheight + 1}: {e}"
                    )
            else:
                log.info("No new blocks to index. Sleeping for 60 seconds ...")
                time.sleep(60)
