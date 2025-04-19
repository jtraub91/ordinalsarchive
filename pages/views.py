import json
from django.core.paginator import Paginator
from django.shortcuts import render
from typing import Optional

from . import models


def index(request):
    results = []
    query = request.GET.get("q")
    if query:
        txins = models.TxIn.objects.filter(scriptsig_text__search=query).all()
        txouts = models.TxOut.objects.filter(scriptpubkey_text__search=query).all()
    else:
        txins = models.TxIn.objects.filter(scriptsig_text__isnull=False).all()
        txouts = models.TxOut.objects.filter(scriptpubkey_text__isnull=False).all()

    for txin in txins:
        results.append(
            {
                "text": txin.scriptsig_text,
                "url": f"/context/{txin.context.id}",
            }
        )
    for txout in txouts:
        results.append(
            {
                "text": txout.scriptpubkey_text,
                "url": f"/context/{txout.context.id}",
            }
        )

    paginator = Paginator(results, 32)
    page = request.GET.get("page")
    results = paginator.get_page(page)
    qd = request.GET.copy()
    if results.has_next():
        qd["page"] = results.next_page_number()
        next_page_url = request.path + "?" + qd.urlencode()
    else:
        next_page_url = None

    if request.headers.get("HX-Request"):
        return render(
            request,
            "components/results.html",
            context={"results": results, "next_page_url": next_page_url},
        )
    return render(
        request,
        "base.html",
        context={"results": results, "next_page_url": next_page_url},
    )


def block(request, blockheaderhash: Optional[str] = None):
    if blockheaderhash is None:
        return render(request, "base.html", context={})
    block = models.Block.objects.filter(blockheaderhash=blockheaderhash).first()
    return render(
        request,
        "block.html",
        context={
            "blockheight": block.blockheight if block else None,
            "blockheaderhash": block.blockheaderhash,
            "blockjson": json.dumps(block.dict(), indent=2),
        },
    )


def context(request, context_id: int):
    context_row = models.ContextRevision.objects.get(id=context_id)
    if inscription := context_row.inscription_set.first():
        content_type = "inscription"
        content = f"/static/inscriptions/{inscription.filename}"
        block = inscription.tx.block
        tx = inscription.tx
        txout = None
        txin = inscription.txin
    elif txin := context_row.txin_set.first():
        content_type = "txin"
        content = txin.scriptsig_text
        block = txin.tx.block
        tx = txin.tx
        txout = None
    elif txout := context_row.txout_set.first():
        content_type = "txout"
        content = txout.scriptpubkey_text
        block = txout.tx.block
        tx = txout.tx
        txin = None
    elif tx := context_row.tx_set.first():
        content_type = "tx"
        content = tx.txid
        block = tx.block
        txout = None
        txin = None
    elif block := context_row.block_set.first():
        content_type = "block"
        content = block.blockheaderhash
        tx = None
        txout = None
        txin = None
    return render(
        request,
        "context.html",
        context={
            "content_type": content_type,
            "content": content,
            "context": context_row.text,
            "blockheight": block.blockheight,
            "blockheaderhash": block.blockheaderhash,
            "txid": tx.txid if tx else None,
            "txout_n": txout.n if txout else None,
            "txin_n": txin.n if txin else None,
        },
    )
