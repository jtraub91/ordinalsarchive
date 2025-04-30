import json
import logging
from mimetypes import guess_extension

import requests
import bits.crypto
import bits.script
from bits import constants
from bits.tx import tx_ser
from bits.blockchain import Block
from django.db import transaction
from django.conf import settings
from django.core.management.base import BaseCommand

import logging
import pages.models
from pages.utils import parse_inscriptions, upload_to_s3, get_object_head_from_s3

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
        parser.add_argument(
            "--reupload-s3",
            action="store_true",
            help="reupload block data to s3",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="delete all db entries created for this index (note: does not delete s3 data or inscription files saved to disk)",
        )

    def handle(
        self,
        blockheight,
        backend,
        reupload_s3: bool = False,
        delete: bool = False,
        **kwargs,
    ):
        if delete:
            num_deleted, deleted_dict = pages.models.Content.objects.filter(
                block__blockheight=blockheight
            ).delete()
            log.info(f"Deleted {num_deleted} entries. {deleted_dict}")
            num_deleted, deleted_dict = pages.models.Inscription.objects.filter(
                txin__tx__block__blockheight=blockheight
            ).delete()
            log.info(f"Deleted {num_deleted} entries. {deleted_dict}")
            num_deleted, deleted_dict = pages.models.CoinbaseScriptsig.objects.filter(
                txin__tx__block__blockheight=blockheight
            ).delete()
            log.info(f"Deleted {num_deleted} entries. {deleted_dict}")
            num_deleted, deleted_dict = pages.models.OpReturn.objects.filter(
                txout__tx__block__blockheight=blockheight
            ).delete()
            log.info(f"Deleted {num_deleted} entries. {deleted_dict}")
            num_deleted, deleted_dict = pages.models.TxIn.objects.filter(
                tx__block__blockheight=blockheight
            ).delete()
            log.info(f"Deleted {num_deleted} entries. {deleted_dict}")
            num_deleted, deleted_dict = pages.models.TxOut.objects.filter(
                tx__block__blockheight=blockheight
            ).delete()
            log.info(f"Deleted {num_deleted} entries. {deleted_dict}")
            num_deleted, deleted_dict = pages.models.Tx.objects.filter(
                block__blockheight=blockheight
            ).delete()
            log.info(f"Deleted {num_deleted} entries. {deleted_dict}")
            num_deleted, deleted_dict = pages.models.Block.objects.filter(
                blockheight=blockheight
            ).delete()
            log.info(f"Deleted {num_deleted} entries. {deleted_dict}")
            return
        if backend == "mempool.space":
            log.info(f"Retrieving block {blockheight} from mempool.space...")
            req = requests.get(f"https://mempool.space/api/block-height/{blockheight}")
            req = requests.get(f"https://mempool.space/api/block/{req.text}/raw")
            log.info(f"Retrieved block {blockheight}.")
            block = Block(req.content)

            if settings.S3_BUCKET_NAME:
                object_exists = get_object_head_from_s3(f"block{blockheight}.bin")
                if not object_exists:
                    log.warning(f"block{blockheight}.bin not found in s3.")
                    log.info(f"Uploading block {blockheight} binary data to s3...")
                    resp = upload_to_s3(f"block{blockheight}.bin", block)
                    log.info(f"block{blockheight}.bin uploaded to s3.")
                elif reupload_s3:
                    log.info(f"block{blockheight}.bin already exists in s3.")
                    log.info(f"Reuploading block {blockheight} binary data to s3...")
                    resp = upload_to_s3(f"block{blockheight}.bin", block)
                    log.info(f"block{blockheight}.bin reuploaded to s3.")
                else:
                    log.info(f"block{blockheight}.bin already exists in s3.")

            log.info(f"Deserializing block {blockheight} ...")
            block_json_data = json.dumps(block.dict(json_serializable=True), indent=2)
            log.info(f"Deserialized block {blockheight}.")
            if settings.S3_BUCKET_NAME:
                object_exists = get_object_head_from_s3(f"block{blockheight}.json")
                if not object_exists:
                    log.warning(f"block{blockheight}.json not found in s3.")
                    log.info(f"Uploading block {blockheight} json data to s3...")
                    resp = upload_to_s3(f"block{blockheight}.json", block_json_data)
                    log.info(f"block{blockheight}.json uploaded to s3.")
                elif reupload_s3:
                    log.info(f"block{blockheight}.json already exists in s3.")
                    log.info(f"Reuploading block {blockheight} json data to s3...")
                    resp = upload_to_s3(f"block{blockheight}.json", block_json_data)
                    log.info(f"block{blockheight}.json reuploaded to s3.")
                else:
                    log.info(f"block{blockheight}.json already exists in s3.")

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
                    coinbase_tx=tx_ser(block["txns"][0]),
                    number_of_txns=len(block["txns"]),
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
                                    block + coinbase_scriptsig_row.scriptsig
                                ),
                                mime_type="text/plain",
                                params={"charset": "utf-8"},
                                size=len(coinbase_scriptsig_row.scriptsig_text),
                                coinbase_scriptsig=coinbase_scriptsig_row,
                                block=block_row,
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
                        if (
                            bytes.fromhex(txout["scriptpubkey"])[0]
                            == constants.OP_RETURN
                        ):
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
                            hash_preimage = f"{opreturn_row.txout.tx.block.blockheaderhash}:{opreturn_row.txout.tx.txid}:{opreturn_row.txout.n}:".encode(
                                "utf8"
                            ) + opreturn_row.scriptpubkey_text.encode(
                                "utf8"
                            )
                            content_row = pages.models.Content(
                                hash=bits.crypto.hash256(hash_preimage),
                                mime_type="text/plain",
                                params={"charset": "utf-8"},
                                size=len(opreturn_row.scriptpubkey_text),
                                op_return=opreturn_row,
                                block=block_row,
                            )
                            content_row.save()
                            log.info(f"{content_row} saved to db.")

                    inscription_index = 0
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
                                log.error(f"Failed to parse inscriptions: {err}")
                                import ipdb

                                ipdb.set_trace()
                                continue
                            for inscription in inscriptions:
                                content_type = inscription["content_type"]
                                content = inscription["data"]
                                content_hash = bits.crypto.hash256(content)
                                content_size = len(content)

                                delegate = inscription.get("delegate")
                                metadata = inscription.get("metadata")
                                pointer = inscription.get("pointer")
                                properties = inscription.get("properties")
                                provenance = inscription.get("provenance")

                                # parse content type
                                content_types = content_type.split(";")
                                mime = content_types[0].strip()
                                mime_type, mime_subtype = mime.split("/")
                                mime_params = {}
                                for param in content_types[1:]:
                                    key, value = param.split("=")
                                    mime_params[key.strip()] = value.strip()

                                if not delegate:
                                    file_ext = guess_extension(mime)
                                    if not file_ext:
                                        log.warning(
                                            f"Couldn't guess extension for {mime}"
                                        )

                                    charset = mime_params.get("charset", "utf-8")
                                    try:
                                        text = content.decode(charset)
                                        json_data = json.loads(text)
                                    except UnicodeDecodeError:
                                        text = None
                                        json_data = None
                                    except json.JSONDecodeError:
                                        json_data = None

                                    if json_data and len(text) < 512:
                                        # json data < 0.5kB not saved to disk
                                        filename = None
                                    elif mime_subtype == "html":
                                        # HTML content saved to disk
                                        filename = f"{content_hash.hex()}{file_ext}"
                                    elif mime_type == "text" and len(text) < 512:
                                        # text content < 0.5kB not saved to disk
                                        filename = None
                                    else:
                                        # all other content saved to disk
                                        filename = (
                                            f"{content_hash.hex()}{file_ext}"
                                            if file_ext
                                            else content_hash.hex()
                                        )
                                    if filename:
                                        filepath = settings.INSCRIPTIONS_DIR / filename
                                        with filepath.open("wb") as fp:
                                            fp.write(content)
                                        log.info(
                                            f"{filename} saved to {settings.INSCRIPTIONS_DIR}"
                                        )

                                inscription_id = f"{txn['txid']}i{inscription_index}"
                                inscription_index += 1
                                inscription_row = pages.models.Inscription(
                                    content_hash=content_hash,
                                    inscription_id=inscription_id,
                                    content_type=content_type,
                                    content_size=content_size,
                                    mime_type=mime_type,
                                    mime_subtype=mime_subtype,
                                    mime_params=mime_params,
                                    filename=filename,
                                    text=text,
                                    json=json_data,
                                    delegate=delegate,
                                    metadata=metadata,
                                    pointer=pointer,
                                    properties=properties,
                                    provenance=provenance,
                                    txin=pages.models.TxIn.objects.get(
                                        tx=tx_row, n=txin_n
                                    ),
                                )
                                inscription_row.save()
                                log.info(f"{inscription_row} saved to db.")

                                hash_preimage = (
                                    inscription_row.inscription_id.encode("utf8")
                                    + b":"
                                    + content
                                )
                                content_row = pages.models.Content(
                                    hash=bits.crypto.hash256(hash_preimage),
                                    mime_type=f"{mime_type}/{mime_subtype}",
                                    size=content_size,
                                    params=mime_params,
                                    inscription=inscription_row,
                                    block=block_row,
                                )
                                content_row.save()
                                log.info(f"{content_row} saved to db.")
        elif backend == "bitcoind":
            raise NotImplementedError
