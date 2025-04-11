import json
import time
from django.shortcuts import render

from . import models


def index(request):
    time_start = time.time()
    context = {}
    query = request.GET.get("q")
    if query:
        results = []
        block_query = models.Block.objects.filter(
            coinbase_tx_scriptsig_text__search=query
        )
        op_return_query = models.OpReturn.objects.filter(text__search=query)
        if block_query:
            for block in block_query.all():
                content = models.Content.objects.filter(block=block).first()
                results.append(
                    {
                        "text": block.coinbase_tx_scriptsig_text,
                        "url": f"/content/{content.id}",
                    }
                )
        if op_return_query:
            for op_return in op_return_query.all():
                content = models.Content.objects.filter(op_return=op_return).first()
                results.append(
                    {"text": op_return.text, "url": f"/content/{content.id}"}
                )
        context["results"] = results
        duration = time.time() - time_start
        if len(results) > 1:
            context["msg"] = (
                f"Found {len(results)} results in {duration:.3f} sec for '{query}'"
            )
        elif len(results) == 1:
            context["msg"] = f"Found 1 result in {duration:.3f} sec for '{query}'"
        else:
            context["msg"] = f"No results found for '{query}'"
        print(results)
    if request.headers.get("HX-Request"):
        return render(request, "components/results.html", context=context)
    return render(request, "base.html", context=context)


def block(request, blockheaderhash):
    _ = models.Block.objects.get(blockheaderhash=blockheaderhash)
    j = json.dumps(
        {
            "blockheaderhash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
            "version": 1,
            "prev_blockheaderhash": "0000000000000000000000000000000000000000000000000000000000000000",
            "merkle_root_hash": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
            "nTime": 1231006505,
            "nBits": "1d00ffff",
            "nNonce": 2083236893,
            "txns": [
                {
                    "txid": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                    "wtxid": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                    "version": 1,
                    "txins": [
                        {
                            "txid": "0000000000000000000000000000000000000000000000000000000000000000",
                            "vout": 4294967295,
                            "scriptsig": "04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73",
                            "sequence": 4294967295,
                        }
                    ],
                    "txouts": [
                        {
                            "value": 5000000000,
                            "scriptpubkey": "4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac",
                        }
                    ],
                    "locktime": 0,
                }
            ],
        },
        indent=2,
    )
    return render(
        request,
        "block.html",
        context={"blockheaderhash": blockheaderhash, "blockjson": j},
    )


def content(request, content_id):
    content = models.Content.objects.get(id=content_id)
    return render(
        request,
        "content.html",
        context={
            "text": content.block.coinbase_tx_scriptsig_text,
            "blockheaderhash": content.block.blockheaderhash,
            "blockheight": content.block.blockheight,
            "context": content.context,
        },
    )
