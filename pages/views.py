import json
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from typing import Optional

from . import models


def index(request):
    results = []
    object_types = request.GET.getlist("object_type")
    content_types = request.GET.getlist("content_type")
    sort = request.GET.get("sort", "relevance")
    order = request.GET.get("order", "asc")
    view = request.GET.get("view", "gallery")
    query = request.GET.get("q")

    filter_query = Q()
    for object_type in object_types:
        if object_type == "inscription":
            for content_type in content_types:
                filter_query |= Q(inscription__isnull=False) & Q(
                    inscription__content_type=content_type
                )
        else:
            kwarg = {f"{object_type}__isnull": False}
            filter_query |= Q(**kwarg)

    objects = models.ContextRevision.objects.filter(filter_query).order_by("-id")

    if query:
        filter_query |= Q(txin__scriptsig_text__search=query)
        filter_query |= Q(txout__scriptpubkey_text__search=query)
        filter_query |= Q(inscription__filename__icontains=query)
        filter_query |= Q(inscription__content_type__icontains=query)
        objects = models.ContextRevision.objects.filter(filter_query)

    paginator = Paginator(objects, 24)
    page = request.GET.get("page")
    page_objects = paginator.get_page(page)

    for obj in page_objects:
        if inscription := obj.inscription_set.first():
            if inscription.filename:
                text = None
                src = f"/static/inscriptions/{inscription.filename}"
            else:
                text = inscription.text
                src = None
        elif txin := obj.txin_set.first():
            text = txin.scriptsig_text
            src = None
        elif txout := obj.txout_set.first():
            text = txout.scriptpubkey_text
            src = None
        elif tx := obj.tx_set.first():
            text = tx.txid
            src = None
        elif block := obj.block_set.first():
            text = block.blockheaderhash
            src = None
        else:
            src = None
            text = str(obj)

        results.append({"text": text, "url": f"/context/{obj.id}", "src": src})

    qd = request.GET.copy()
    if page_objects.has_next():
        qd["page"] = page_objects.next_page_number()
        next_page_url = request.path + "?" + qd.urlencode()
    else:
        next_page_url = None

    if request.headers.get("HX-Request"):
        return render(
            request,
            "components/results.html",
            context={"results": results, "next_page_url": next_page_url},
        )
    content_types = models.Inscription.objects.values_list(
        "content_type", flat=True
    ).distinct()
    return render(
        request,
        "base.html",
        context={
            "results": results,
            "next_page_url": next_page_url,
            "object_types": ["Inscription", "TxIn", "TxOut", "Tx", "Block"],
            "content_types": content_types,
        },
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
        object_type = "Inscription"
        if inscription.filename:
            content = f"/static/inscriptions/{inscription.filename}"
            content_size = inscription.content_size
        else:
            content = inscription.text
            content_size = inscription.content_size
        content_type = inscription.content_type
        block = inscription.txin.tx.block
        tx = inscription.txin.tx
        txout = None
        txin = inscription.txin
    elif txin := context_row.txin_set.first():
        object_type = "Txin"
        content = txin.scriptsig_text
        content_size = len(txin.scriptsig_text) if txin.scriptsig_text else 0
        content_type = "text/plain;charset=utf8"
        block = txin.tx.block
        tx = txin.tx
        txout = None
    elif txout := context_row.txout_set.first():
        object_type = "Txout"
        content = txout.scriptpubkey_text
        content_size = len(txout.scriptpubkey_text) if txout.scriptpubkey_text else 0
        content_type = "text/plain;charset=utf8"
        block = txout.tx.block
        tx = txout.tx
        txin = None
    elif tx := context_row.tx_set.first():
        object_type = "Tx"
        content = tx.txid
        content_size = len(tx.txid)
        content_type = "text/plain;charset=utf8"
        block = tx.block
        txout = None
        txin = None
    elif block := context_row.block_set.first():
        object_type = "Block"
        content = block.blockheaderhash
        content_size = len(block.blockheaderhash)
        content_type = "text/plain;charset=utf8"
        tx = None
        txout = None
        txin = None
    return render(
        request,
        "context.html",
        context={
            "object_type": object_type,
            "content_type": content_type,
            "content": content,
            "content_size": content_size,
            "context": context_row.text,
            "blockheight": block.blockheight,
            "blockheaderhash": block.blockheaderhash,
            "txid": tx.txid if tx else None,
            "txout_n": txout.n if txout else None,
            "txin_n": txin.n if txin else None,
        },
    )
