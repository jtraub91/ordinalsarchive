import requests
import bits.script
from bits.blockchain import Block
from django.core.management.base import BaseCommand, CommandError

from pages import models


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
            ret = {}
            req = requests.get(f"https://mempool.space/api/block-height/{blockheight}")
            blockheaderhash = req.text
            ret["blockheight"] = blockheight
            ret["blockheaderhash"] = blockheaderhash
            req = requests.get(f"https://mempool.space/api/block/{blockheaderhash}/raw")
            block = Block(req.content)
            coinbase_tx_scriptsig = block["txns"][0]["txins"][0]["scriptsig"]
            block_row = models.Block(
                blockheight=blockheight,
                blockheaderhash=block["blockheaderhash"],
                version=block["version"],
                prev_blockheaderhash=block["prev_blockheaderhash"],
                merkle_root=block["merkle_root_hash"],
                time=block["nTime"],
                bits=block["nBits"],
                nonce=block["nNonce"],
                coinbase_tx_scriptsig=coinbase_tx_scriptsig,
                coinbase_tx_scriptsig_text=bytes.fromhex(coinbase_tx_scriptsig)
                .decode("utf8", "ignore")
                .replace("\x00", ""),
            )
            block_row.save()
            self.stdout.write(f"{block_row} saved to db.")
            content_row = models.Content(context="", block=block_row)
            content_row.save()
            self.stdout.write(f"{content_row} saved to db.")
            txns = block["txns"]
            for txn in txns:
                tx_row = models.Tx(
                    txid=txn["txid"],
                    wtxid=txn["wtxid"],
                    version=txn["version"],
                    locktime=txn["locktime"],
                    block=block_row,
                )
                for n, txout_ in enumerate(txn["txouts"]):
                    scriptpubkey = txout_["scriptpubkey"]
                    decoded_script = bits.script.decode_script(
                        bytes.fromhex(scriptpubkey)
                    )
                    # TODO: validate decoded script is a valid op_return script
                    if "OP_RETURN" in decoded_script:
                        op_return_row = models.OpReturn(
                            data=decoded_script[1],
                            text=bytes.fromhex(decoded_script[1]).decode(
                                "utf8", "ignore"
                            ),
                            txout_n=n,
                            txout_value=txout_["value"],
                        )
                        op_return_row.save()
                        self.stdout.write(f"{op_return_row} saved to db.")
                        content_row = models.Content(
                            context="", op_return=op_return_row
                        )
                        content_row.save()
                        self.stdout.write(f"{content_row} saved to db.")
                tx_row.save()
                self.stdout.write(f"{tx_row} saved to db.")
        elif backend == "bitcoind":
            raise NotImplementedError
