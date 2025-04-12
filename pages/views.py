import json
import time
from django.shortcuts import render
from typing import Optional

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
    else:
        results = []
        contents = models.Content.objects.all()
        for content in contents:
            if content.op_return:
                results.append(
                    {
                        "text": content.op_return.text,
                        "url": f"/content/{content.id}",
                    }
                )
            elif content.block:
                results.append(
                    {
                        "text": content.block.coinbase_tx_scriptsig_text,
                        "url": f"/content/{content.id}",
                    }
                )
        context = {
            "msg": f"Showing all results. Found {len(results)} in {time.time() - time_start:.3f} sec",
            "results": results,
        }
    if request.headers.get("HX-Request"):
        return render(request, "components/results.html", context=context)
    return render(request, "base.html", context=context)


def block(request, blockheaderhash: Optional[str] = None):
    if blockheaderhash is None:
        return render(request, "base.html", context={})
    block_index = models.Block.objects.get(blockheaderhash=blockheaderhash)
    return render(
        request,
        "block.html",
        context={
            "blockheaderhash": blockheaderhash,
            "blockjson": json.dumps(block_index.dict(), indent=2),
        },
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
