import requests
import bits.crypto
import bits.script
from bits.blockchain import Block
from django.db import transaction
from django.conf import settings
from django.core.management.base import BaseCommand

import pages.models


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
            self.stdout.write(f"Retrieving block {blockheight} from mempool.space...")
            req = requests.get(f"https://mempool.space/api/block-height/{blockheight}")
            req = requests.get(f"https://mempool.space/api/block/{req.text}/raw")
            self.stdout.write(f"Retrieved block {blockheight}.")
            block = Block(req.content)
            self.stdout.write(f"Deserializing block {blockheight} ...")
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
                self.stdout.write(f"{block_row} saved to db.")
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
                    self.stdout.write(f"{tx_row} saved to db.")
                    for txin_n, txin in enumerate(txn["txins"]):
                        txin_row = pages.models.TxIn(
                            tx=tx_row,
                            n=txin_n,
                            txid=txin["txid"],
                            vout=txin["vout"],
                            # only store script sig text of coinbase tx
                            scriptsig_text=(
                                bytes.fromhex(txin["scriptsig"])
                                .decode("utf8", "ignore")
                                .replace("\x00", "")
                                if txn_n == 0
                                else None
                            ),
                            sequence=txin["sequence"],
                        )
                        txin_row.save()
                        self.stdout.write(f"{txin_row} saved to db.")

                    for txout_n, txout in enumerate(txn["txouts"]):
                        scriptpubkey = txout["scriptpubkey"]
                        decoded_script = bits.script.decode_script(
                            bytes.fromhex(scriptpubkey)
                        )
                        txout_row = pages.models.TxOut(
                            tx=tx_row,
                            n=txout_n,
                            scriptpubkey=(
                                bytes.fromhex(scriptpubkey)
                                if "OP_RETURN" in decoded_script
                                else None
                            ),
                            scriptpubkey_text=(
                                bytes.fromhex(decoded_script[1])
                                .decode("utf8", "ignore")
                                .replace("\x00", "")
                                if "OP_RETURN" in decoded_script
                                else None
                            ),
                            value=txout["value"],
                        )
                        txout_row.save()
                        self.stdout.write(f"{txout_row} saved to db.")

                    for txin_n, txin_witness_stack in enumerate(
                        txn.get("witnesses", [])
                    ):
                        for elem in txin_witness_stack:
                            if b"\x00\x63\x03ord" in elem:
                                envelope = elem.split(b"\x00\x63\x03ord")[1]
                                if envelope[0:1] != b"\x01":
                                    continue
                                if envelope[1:2] != b"\x01":
                                    continue
                                envelope = envelope[2:]
                                content_type_len, envelope = (
                                    bits.parse_compact_size_uint(envelope)
                                )
                                content_type = envelope[:content_type_len].decode(
                                    "utf8"
                                )
                                envelope = envelope[content_type_len:]
                                decoded = bits.script.decode_script(envelope)
                                data = "".join(decoded[1:-1])
                                data = bytes.fromhex(data)
                                # TODO: ^ this logic sorta flaky and will fail for cursed inscriptions
                                filename = f"{bits.crypto.hash256(data).hex()}.{content_type.split('/')[1]}"
                                with open(
                                    settings.INSCRIPTIONS_DIR / filename, "wb"
                                ) as f:
                                    f.write(data)
                                self.stdout.write(
                                    f"{filename} saved to {settings.INSCRIPTIONS_DIR}"
                                )
                                inscription_row = pages.models.Inscription(
                                    content_type=content_type,
                                    content_size=len(data),
                                    filename=filename,
                                    txin=pages.models.TxIn.objects.get(
                                        tx=tx_row, n=txin_n
                                    ),
                                )
                                inscription_row.save()
                                self.stdout.write(f"{inscription_row} saved to db.")

        elif backend == "bitcoind":
            raise NotImplementedError
