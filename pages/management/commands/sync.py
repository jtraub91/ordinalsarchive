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
        current_blockheight = Block.objects.order_by("-blockheight").first().blockheight
        req = requests.get(f"https://mempool.space/api/blocks/tip/height")
        mempool_blockheight = int(req.text)

        if current_blockheight < mempool_blockheight:
            for blockheight in range(current_blockheight + 1, mempool_blockheight + 1):
                log.info(f"Indexing block {blockheight}...")
                try:
                    call_command("index", blockheight, reupload_s3=True)
                except Exception as e:
                    log.error(f"Failed to index block {blockheight}: {e}")

        while True:
            req = requests.get(f"https://mempool.space/api/blocks/tip/height")
            blockchain_height = int(req.text)
            log.info(f"Blockchain height per mempool.space: {blockchain_height}")
            try:
                call_command("index", blockchain_height, reupload_s3=True)
            except Exception as e:
                log.error(f"Failed to index block {blockchain_height}: {e}")
            log.info("Sleeping for 60 seconds...")
            time.sleep(60)
