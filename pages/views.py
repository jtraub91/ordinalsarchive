import json
import os
from datetime import datetime, timezone
from typing import Optional

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from . import models


def index(request):
    results = []

    # query parameters
    object_types = request.GET.getlist("object_type")
    content_types = request.GET.getlist("content_type")
    sort = request.GET.get("sort", "date")
    order = request.GET.get("order", "asc")
    view = request.GET.get("view", "gallery")
    query = request.GET.get("q")  # search query

    # Get all possible object types/content types
    all_object_types = ["inscription", "txin", "txout", "tx", "block"]
    all_content_types = list(
        models.Inscription.objects.values_list("content_type", flat=True).distinct()
    )

    # If all or none object types are selected, treat as no filtering
    if not object_types or set(object_types) == set(all_object_types):
        object_types = all_object_types
    # If inscription is selected but no content types, treat as all content types
    if "inscription" in object_types:
        if not content_types or set(content_types) == set(all_content_types):
            content_types = all_content_types
    else:
        content_types = []  # Ignore content types if inscription not selected

    filter_query = Q()

    if "inscription" in object_types:
        # If inscription, filter by all selected content types
        ct_q = Q()
        for content_type in content_types:
            ct_q |= Q(inscription__isnull=False) & Q(
                inscription__content_type=content_type
            )
        filter_query &= ct_q
    if "txin" in object_types:
        filter_query |= Q(txin__isnull=False) & Q(txin__scriptsig_text__isnull=False)
    if "txout" in object_types:
        filter_query |= Q(txout__isnull=False) & Q(
            txout__scriptpubkey_text__isnull=False
        )
    if "tx" in object_types:
        filter_query |= Q(tx__isnull=False) & Q(tx__txid__isnull=False)
    if "block" in object_types:
        filter_query |= Q(block__isnull=False) & Q(block__blockheaderhash__isnull=False)

    # Main queryset
    objects = models.ContextRevision.objects.filter(filter_query)
    # import ipdb; ipdb.set_trace()
    # Apply search query as AND
    if query:
        q_filter = (
            Q(txin__scriptsig_text__icontains=query)
            | Q(txout__scriptpubkey_text__icontains=query)
            | Q(inscription__filename__icontains=query)
            | Q(inscription__content_type__icontains=query)
            | Q(inscription__text__icontains=query)
            | Q(html__icontains=query)
        )
        objects = objects.filter(q_filter)

    # Sorting (default to date for now)
    if sort == "date":
        objects = objects.order_by("-block_time" if order == "desc" else "block_time")
    else:
        # Placeholder for relevance (use date for now)
        objects = objects.order_by("-block_time" if order == "desc" else "block_time")

    paginator = Paginator(objects, 24)
    page = request.GET.get("page")
    page_objects = paginator.get_page(page)

    for ctx in page_objects:
        if inscription := ctx.inscription_set.first():
            if inscription.filename:
                text = None
                src = f"/static/inscriptions/{inscription.filename}"
                text_json = None
            else:
                text = inscription.text
                try:
                    text_json = json.loads(text)
                except json.JSONDecodeError:
                    text_json = None
                src = None
            blockheight = inscription.txin.tx.block.blockheight
            txid = inscription.txin.tx.txid
            random = None
        elif txin := ctx.txin_set.first():
            text = txin.scriptsig_text
            src = None
            blockheight = txin.tx.block.blockheight
            txid = txin.tx.txid
            random = bin(int.from_bytes(os.urandom(128)))
            text_json = None
        elif txout := ctx.txout_set.first():
            text = txout.scriptpubkey_text
            src = None
            blockheight = txout.tx.block.blockheight
            txid = txout.tx.txid
            random = bin(int.from_bytes(os.urandom(128)))
            text_json = None
        elif tx := ctx.tx_set.first():
            text = tx.txid
            src = None
            blockheight = tx.block.blockheight
            txid = tx.txid
            random = None
            text_json = None
        elif block := ctx.block_set.first():
            text = block.blockheaderhash
            blockheight = block.blockheight
            src = None
            txid = None
            random = None
            text_json = None
        else:
            src = None
            text = str(ctx)
            blockheight = None
            txid = None
            random = None
            text_json = None
        strf_format = "%Y-%m-%d %H:%M:%S %Z"
        block_timestamp = datetime.fromtimestamp(
            ctx.block_time, tz=timezone.utc
        ).strftime(strf_format)

        results.append(
            {
                "context_revision": ctx,
                "url": f"/context/{ctx.id}",
                "src": src,
                "text": text,
                "text_json": text_json,
                "brc_20": True if text_json else False,
                "blockheight": blockheight,
                "block_timestamp": block_timestamp,
                "txid": txid,
                "random": random,
            }
        )

    qd = request.GET.copy()
    if page_objects.has_next():
        qd["page"] = page_objects.next_page_number()
        next_page_url = request.path + "?" + qd.urlencode()
    else:
        next_page_url = None

    query_object_types = request.GET.getlist("object_type")
    query_content_types = request.GET.getlist("content_type")

    if request.headers.get("HX-Request"):
        return render(
            request,
            "components/results.html",
            context={
                "results": results,
                "next_page_url": next_page_url,
                "object_types": ["Inscription", "TxIn", "TxOut", "Tx", "Block"],
                "content_types": content_types,
                "query_object_types": query_object_types,
                "query_content_types": query_content_types,
            },
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
            "view": view,
            "query_object_types": query_object_types,
            "query_content_types": query_content_types,
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
            "blockjson": json.dumps(
                {
                    "blockheight": block.blockheight,
                    "blockheaderhash": block.blockheaderhash,
                    "version": block.version,
                    "prev_blockheaderhash": block.prev_blockheaderhash,
                    "merkle_root": block.merkle_root,
                    "time": block.time,
                    "bits": block.bits,
                    "nonce": block.nonce,
                },
                indent=2,
            ),
        },
    )


def context_revision(request, context_id):
    if request.method == "POST":
        context_html = request.POST["context_html"]
        context_ = get_object_or_404(models.ContextRevision, id=context_id)
        context_.html = context_html
        context_.save()
        return render(
            request,
            "components/context_editor.html",
            context={"context_html": context_html, "context_id": context_.id},
        )
    else:  # GET
        context_ = get_object_or_404(models.ContextRevision, id=context_id)
        return render(
            request,
            "components/context_editor.html",
            context={"context_html": context_.html, "context_id": context_.id},
        )


def context(request, context_id: int):
    context_row = models.ContextRevision.objects.get(id=context_id)
    if inscription := context_row.inscription_set.first():
        object_type = "Inscription"
        if inscription.filename:
            content_src = f"/static/inscriptions/{inscription.filename}"
            content_text = None
            content_size = inscription.content_size
        else:
            content_src = None
            content_text = inscription.text
            content_size = inscription.content_size
        content_type = inscription.content_type
        block = inscription.txin.tx.block
        tx = inscription.txin.tx
        txout = None
        txin = inscription.txin
    elif txin := context_row.txin_set.first():
        object_type = "Txin"
        content_src = None
        content_text = txin.scriptsig_text
        content_size = len(txin.scriptsig_text) if txin.scriptsig_text else 0
        content_type = "text/plain;charset=utf8"
        block = txin.tx.block
        tx = txin.tx
        txout = None
    elif txout := context_row.txout_set.first():
        object_type = "Txout"
        content_src = None
        content_text = txout.scriptpubkey_text
        content_size = len(txout.scriptpubkey_text) if txout.scriptpubkey_text else 0
        content_type = "text/plain;charset=utf8"
        block = txout.tx.block
        tx = txout.tx
        txin = None
    elif tx := context_row.tx_set.first():
        object_type = "Tx"
        content_src = None
        content_text = tx.txid
        content_size = len(tx.txid)
        content_type = "text/plain;charset=utf8"
        block = tx.block
        txout = None
        txin = None
    elif block := context_row.block_set.first():
        object_type = "Block"
        content_src = None
        content_text = block.blockheaderhash
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
            "content_src": content_src,
            "content_text": content_text,
            "content_size": content_size,
            "context_html": context_row.html,
            "context_id": context_row.id,
            "blockheight": block.blockheight,
            "blockheaderhash": block.blockheaderhash,
            "tx_n": tx.n if tx else None,
            "txid": tx.txid if tx else None,
            "txout_n": txout.n if txout else None,
            "txin_n": txin.n if txin else None,
        },
    )
