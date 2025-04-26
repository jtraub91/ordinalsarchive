from mimetypes import guess_extension

import json
import logging
import requests
import bits.crypto
import bits.script
from bits import constants
from bits.blockchain import Block
from django.db import transaction
from django.conf import settings
from django.core.management.base import BaseCommand

import logging
import pages.models
from pages.utils import parse_inscriptions, upload_to_s3

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Retrieve and index block data, parse static content"

    def add_arguments(self, parser):
        parser.add_argument(
            "blockheight", type=int, help="the height of block to index"
        )
        parser.add_argument(
            "--backend",
            choices=["mempool.space", "bitcoind"],
            default="mempool.space",
            help="backend to use for retrieving raw block data to be parsed and indexed",
        )

    def handle(self, blockheight, backend, **kwargs):
        if backend == "mempool.space":
            log.info(f"Retrieving block {blockheight} from mempool.space...")
            req = requests.get(f"https://mempool.space/api/block-height/{blockheight}")
            req = requests.get(f"https://mempool.space/api/block/{req.text}/raw")
            log.info(f"Retrieved block {blockheight}.")
            block = Block(req.content)
            log.info(f"Uploading block {blockheight} to s3...")
            if settings.DJANGO_S3_BUCKET_NAME:
                resp = upload_to_s3(f"block{blockheight}.bin", block)
                log.info(f"Block{blockheight}.bin uploaded to s3.")
                if resp["HTTPStatusCode"] >= 200 and resp["HTTPStatusCode"] < 400:
                    log.info(f"Block{blockheight}.bin uploaded to s3.")
                else:
                    log.debug(resp)
                    log.warning(
                        f"Upload block{blockheight}.bin to s3 failed with HTTP Status Code {resp['HTTPStatusCode']}"
                    )

            log.info(f"Deserializing block {blockheight} ...")
            block_json_data = block.dict(json_serializable=True)
            if settings.DJANGO_S3_BUCKET_NAME:
                resp = upload_to_s3(f"block{blockheight}.json", block_json_data)
                if resp["HTTPStatusCode"] >= 200 and resp["HTTPStatusCode"] < 400:
                    log.info(f"Block{blockheight}.json uploaded to s3.")
                else:
                    log.debug(resp)
                    log.warning(
                        f"Upload block{blockheight}.json to s3 failed with HTTP Status Code {resp['HTTPStatusCode']}"
                    )

            log.info(f"Deserialized block {blockheight}.")
            with transaction.atomic():
                block_row = pages.models.Block(
                    blockheight=blockheight,
                    blockheaderhash=block["blockheaderhash"],
                    version=block["version"],
                    prev_blockheaderhash=block["prev_blockheaderhash"],
                    merkle_root=block["merkle_root_hash"],
                    time=block["nTime"],
                    bits=block["nBits"],
                    nonce=block["nNonce"],
                )
                block_row.save()
                log.info(f"{block_row} saved to db.")
                for txn_n, txn in enumerate(block["txns"]):
                    tx_row = pages.models.Tx(
                        block=block_row,
                        n=txn_n,
                        txid=txn["txid"],
                        wtxid=txn["wtxid"],
                        version=txn["version"],
                        locktime=txn["locktime"],
                    )
                    tx_row.save()
                    log.info(f"{tx_row} saved to db.")
                    for txin_n, txin in enumerate(txn["txins"]):
                        txin_row = pages.models.TxIn(
                            tx=tx_row,
                            n=txin_n,
                            txid=txin["txid"],
                            vout=txin["vout"],
                            sequence=txin["sequence"],
                        )
                        txin_row.save()
                        log.info(f"{txin_row} saved to db.")
                        # only store script sig text of coinbase tx
                        if txn_n == 0:
                            coinbase_scriptsig_row = pages.models.CoinbaseScriptsig(
                                txin=txin_row,
                                scriptsig=bytes.fromhex(txin["scriptsig"]),
                                scriptsig_text=bytes.fromhex(txin["scriptsig"])
                                .decode("utf8", "ignore")
                                .replace("\x00", ""),
                            )
                            coinbase_scriptsig_row.save()
                            log.info(f"{coinbase_scriptsig_row} saved to db.")

                            content_row = pages.models.Content(
                                hash=bits.crypto.hash256(
                                    coinbase_scriptsig_row.scriptsig_text.encode("utf8")
                                ),
                                mime_type="text/plain",
                                params={"charset": "utf-8"},
                                size=len(coinbase_scriptsig_row.scriptsig_text),
                                coinbase_scriptsig=coinbase_scriptsig_row,
                            )
                            content_row.save()
                            log.info(f"{content_row} saved to db.")

                    for txout_n, txout in enumerate(txn["txouts"]):
                        txout_row = pages.models.TxOut(
                            tx=tx_row,
                            n=txout_n,
                            value=txout["value"],
                        )
                        txout_row.save()
                        log.info(f"{txout_row} saved to db.")
                        if txout["scriptpubkey"][0] == constants.OP_RETURN:
                            opreturn_row = pages.models.OpReturn(
                                txout=txout_row,
                                scriptpubkey=bytes.fromhex(txout["scriptpubkey"]),
                                scriptpubkey_text=bytes.fromhex(txout["scriptpubkey"])
                                .decode("utf8", "ignore")
                                .replace("\x00", ""),
                            )
                            opreturn_row.save()
                            log.info(f"{opreturn_row} saved to db.")

                            # TODO: maybe parse OP_RETURN for more types of content, counterparty? exsat?
                            content_row = pages.models.Content(
                                hash=bits.crypto.hash256(
                                    opreturn_row.scriptpubkey_text.encode("utf8")
                                ),
                                mime_type="text/plain",
                                params={"charset": "utf-8"},
                                size=len(opreturn_row.scriptpubkey_text),
                                op_return=opreturn_row,
                            )
                            content_row.save()
                            log.info(f"{content_row} saved to db.")

                    for txin_n, txin_witness_stack in enumerate(
                        txn.get("witnesses", [])
                    ):
                        log.info(
                            f"Parsing witness of txin {txin_n} of txn {txn_n} of block {blockheight}..."
                        )
                        for elem_i, elem in enumerate(txin_witness_stack):
                            try:
                                inscriptions = parse_inscriptions(elem)
                            except ValueError as err:
                                log.error(
                                    f"Error parsing inscriptions from witness stack element {elem_i} for txin {txin_n} from txn {txn_n} of block {blockheight}: {err}"
                                )
                                continue
                            for inscription in inscriptions:
                                content_type = inscription["content_type"]
                                content = inscription["data"]
                                content_hash = bits.crypto.hash256(content)
                                content_size = len(content)

                                # parse content type
                                content_types = content_type.split(";")
                                mime_type = content_types[0].strip()
                                params = {}
                                for param in content_types[1:]:
                                    key, value = param.split("=")
                                    params[key.strip()] = value.strip()

                                try:
                                    text = content.decode("utf8")
                                    json_data = json.loads(text)
                                except UnicodeDecodeError:
                                    text = None
                                    json_data = {}
                                except json.JSONDecodeError:
                                    json_data = {}

                                file_ext = guess_extension(mime_type)
                                log.warning(f"Couldn't guess extension for {mime_type}")

                                if content_size > 1024:
                                    filename = (
                                        f"{content_hash.hex()}.{file_ext}"
                                        if file_ext
                                        else content_hash.hex()
                                    )
                                    filepath = settings.INSCRIPTIONS_DIR / filename

                                    with filepath.open("wb") as fp:
                                        fp.write(content)
                                    log.info(
                                        f"{filename} saved to {settings.INSCRIPTIONS_DIR}"
                                    )
                                    text = None
                                    json_data = {}
                                else:
                                    filename = None

                                inscription_row = pages.models.Inscription(
                                    hash=content_hash,
                                    content_type=content_type,
                                    size=content_size,
                                    params=params,
                                    filename=filename,
                                    text=text,
                                    json=json_data,
                                    txin=pages.models.TxIn.objects.get(
                                        tx=tx_row, n=txin_n
                                    ),
                                )
                                inscription_row.save()
                                log.info(f"{inscription_row} saved to db.")

                                content = pages.models.Content(
                                    hash=content_hash,
                                    mime_type=mime_type,
                                    size=content_size,
                                    params=params,
                                    inscription=inscription_row,
                                    block=block_row,
                                )
                                content.save()
                                log.info(f"{content} saved to db.")
        elif backend == "bitcoind":
            raise NotImplementedError
