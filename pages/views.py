import json
from datetime import datetime, timezone

import bits.crypto
import bits.bips.bip39
import cbor2
from bits.blockchain import Block
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from . import models
from .utils import get_object_from_s3


def content_types(request):
    mime_types = models.Content.objects.values_list("mime_type", flat=True).distinct()
    return render(request, "components/content_types.html", {"mime_types": mime_types})


def index(request):
    results = []

    # query parameters
    object_types = request.GET.getlist(
        "object_type", ["inscription", "opreturn", "coinbase"]
    )
    mime_types = request.GET.getlist("mime_type")
    sort = request.GET.get("sort", "date")
    order = request.GET.get("order", "desc")
    view = request.GET.get("view", "gallery")
    query = request.GET.get("q")  # search query

    q = Q()
    if query:
        q = (
            Q(coinbase_scriptsig__scriptsig_text__icontains=query)
            | Q(op_return__scriptpubkey_text__icontains=query)
            | Q(inscription__content_type__icontains=query)
            | Q(inscription__text__icontains=query)
            | Q(context_revision__html__search=query)
        )

    content_objects = models.Content.objects.filter(q).order_by(
        "-block__time" if order == "desc" else "block__time"
    )
    content_objects = content_objects.filter(inscription__json__isnull=True)

    q = Q()
    if "inscription" not in object_types:
        q = q & Q(inscription__isnull=True)
    if "opreturn" not in object_types:
        q = q & Q(op_return__isnull=True)
    if "coinbase" not in object_types:
        q = q & Q(coinbase_scriptsig__isnull=True)
    content_objects = content_objects.filter(q)

    if mime_types:
        q = Q()
        for mime_type in mime_types:
            q = q | Q(mime_type=mime_type)
        content_objects = content_objects.filter(q)

    paginator = Paginator(content_objects, 12)
    page = request.GET.get("page")
    page_objects = paginator.get_page(page)

    # block_objects = models.Block.objects.order_by("-time" if order == "desc" else "time")
    # tx_objects = models.Tx.objects.order_by("-block__time" if order == "desc" else "block__time")

    # def sort_fn(o):
    #     if hasattr(o, "time"):
    #         return o.time
    #     else:
    #         return o.block.time

    # objects = sorted(list(content_objects) + list(block_objects) + list(tx_objects), key=sort_fn, reverse=True if order == "desc" else False)

    # paginator = Paginator(objects, 24)
    # page = request.GET.get("page")
    # page_objects = paginator.get_page(page)

    for obj in page_objects:
        if isinstance(obj, models.Content):
            if obj.inscription:
                object_type = "Inscription"
                src = (
                    f"/static/inscriptions/{obj.inscription.filename}"
                    if obj.inscription.filename
                    else None
                )
                text = obj.inscription.text
                text_json = obj.inscription.json
                block = obj.inscription.txin.tx.block
                txid = obj.inscription.txin.tx.txid
            elif obj.op_return:
                object_type = "OpReturn"
                src = None
                text = obj.op_return.scriptpubkey_text
                text_json = None
                block = obj.op_return.txout.tx.block
                txid = obj.op_return.txout.tx.txid
            elif obj.coinbase_scriptsig:
                object_type = "CoinbaseScriptsig"
                src = None
                text = obj.coinbase_scriptsig.scriptsig_text
                text_json = None
                block = obj.coinbase_scriptsig.txin.tx.block
                txid = obj.coinbase_scriptsig.txin.tx.txid
            else:
                return HttpResponseBadRequest()
            url = f"/context/{obj.context_revision.id}"
        elif isinstance(obj, models.Block):
            object_type = "Block"
            src = None
            text = None
            text_json = None
            block = obj
            txid = None
            url = f"/block/{obj.blockheaderhash}"
        elif isinstance(obj, models.Tx):
            object_type = "Tx"
            src = None
            text = None
            text_json = None
            block = obj.block
            txid = obj.txid
            url = f"/tx/{obj.txid}"
        else:
            return HttpResponseBadRequest()

        block_timestamp = datetime.fromtimestamp(block.time, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )

        results.append(
            {
                "object_type": object_type,
                "content": obj,
                "mime_type": obj.mime_type.split("/")[0],
                "mime_subtype": obj.mime_type.split("/")[1],
                "url": url,
                "src": src,
                "text": text,
                "text_json": text_json,
                "blockheight": block.blockheight,
                "block_timestamp": block_timestamp,
                "txid": txid,
                "block_binary": Block(block.serialized()).bin(),
            }
        )

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
            context={
                "results": results,
                "next_page_url": next_page_url,
            },
        )
    return render(
        request,
        "base.html",
        context={
            "results": results,
            "next_page_url": next_page_url,
        },
    )


def block(request, blockheaderhash: str):
    offset = request.GET.get("offset", 0)
    limit = request.GET.get("limit", 4096)
    fmt = request.GET.get("fmt", "hex")

    block = get_object_or_404(models.Block, blockheaderhash=blockheaderhash)

    block_data = get_object_from_s3(
        f"block{block.blockheight}.bin", offset=offset
    ).read(limit)
    # block_json = get_object_from_s3(f"block{block.blockheight}.json").read(MAX_BYTES).decode("utf-8")
    if request.headers.get("Content-Type") == "application/json":
        return JsonResponse(
            {
                "blockhex": block_data.hex(),
            }
        )
    return render(
        request,
        "block.html",
        context={
            "next_offset": int(offset) + 2**12,
            "blockheight": block.blockheight if block else None,
            "blockheaderhash": block.blockheaderhash,
            "blockhex": block_data.hex(),
            # "blockjson": block_json,
        },
    )


def tx(request, txid: str):
    tx = get_object_or_404(models.Tx, txid=txid)
    block_data = get_object_from_s3(f"block{tx.block.blockheight}.bin").read()
    block = Block(block_data).dict(json_serializable=True)
    tx_json = json.dumps(
        next(filter(lambda tx_: tx_["txid"] == txid, block["txns"])), indent=2
    )
    return render(
        request,
        "tx.html",
        context={
            "txid": tx.txid if tx else None,
            "txjson": tx_json,
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
    content = context_row.content_set.first()
    if content.inscription:
        object_type = "Inscription"
        if content.inscription.metadata:
            metadata = cbor2.loads(content.inscription.metadata)
        else:
            metadata = {}
    elif content.coinbase_scriptsig:
        object_type = "CoinbaseScriptsig"
        metadata = {}
    elif content.op_return:
        object_type = "OpReturn"
        metadata = {}
    else:
        return HttpResponseBadRequest()
    block_timestamp = datetime.fromtimestamp(
        content.block.time, tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M:%S %Z")

    content_type = f"{content.mime_type}; "
    for key, value in content.params.items():
        content_type += f"{key}={value}; "
    return render(
        request,
        "context.html",
        context={
            "object_type": object_type,
            "block_timestamp": block_timestamp,
            "content": content,
            "content_type": content_type,
            "content_metadata": metadata,
            "mime_type": content.mime_type.split("/")[0],
            "context": context_row,
            "context_revision_hash": bits.crypto.hash256(
                (str(context_row.id) + context_row.html).encode("utf-8")
            ).hex(),
        },
    )
