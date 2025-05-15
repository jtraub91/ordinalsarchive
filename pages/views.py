import base64
import io
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import bits.bips.bip39
import bits.crypto
import cbor2
import qrcode
from bits import to_bitcoin_address
from bits.blockchain import Block
from bits.bips.bip32 import deserialized_extended_key
from bits.wallet.hd import derive_from_path
from django.http import JsonResponse, HttpResponseBadRequest, FileResponse
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.shortcuts import render, get_object_or_404
from glclient import Credentials, Scheduler, clnpb


from . import models
from .utils import get_object_from_s3, get_object_head_from_s3, readable_size


log = logging.getLogger(__name__)


def block_height(request):
    latest_block = models.Block.objects.order_by("-blockheight").first()
    return JsonResponse(
        {
            "block_height": latest_block.blockheight,
            "block_time": latest_block.time,
            "block_timestamp": datetime.fromtimestamp(
                latest_block.time, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S %Z"),
        }
    )


def content_types(request):
    # mime_type in the content model is actually {mime_type}/{mime_subtype}
    # TODO: content model needs to be reworked or removed, but maybe can eventually be refactored for search indexing
    mime_types = models.Content.objects.values_list("mime_type", flat=True).distinct()
    return render(request, "components/content_types.html", {"mime_types": mime_types})


def index(request):
    results = []

    mime_types = request.GET.getlist("mime_type")
    order = request.GET.get("order", "desc")
    # sort = request.GET.get("sort", "date")
    # view = request.GET.get("view", "gallery")
    filters = request.GET.getlist("filter")
    start = request.GET.get("start")
    end = request.GET.get("end")
    query = request.GET.get("q")

    content_query = Q()
    for filter_ in filters:
        if filter_ in ["inscription", "op_return", "coinbase_scriptsig"]:
            kwarg = {f"{filter_}__isnull": True}
            content_query &= Q(**kwarg)
        elif filter_ == "brc-20":
            content_query &= Q(is_brc20=False)
    content_objects = models.Content.objects.filter(content_query).select_related(
        "inscription", "op_return", "coinbase_scriptsig"
    )

    content_query = Q()
    if mime_types:
        for mime_type in mime_types:
            if mime_type == "other":
                content_query |= (
                    ~Q(mime_type="text")
                    & ~Q(mime_type="image")
                    & ~Q(mime_type="audio")
                    & ~Q(mime_type="video")
                )
            else:
                content_query |= Q(mime_type=mime_type)
        content_objects = content_objects.filter(content_query)

    content_query = Q()
    if start is not None:
        print(start)
        content_query &= Q(block_height__gte=int(start))
    if end is not None and end != "":
        content_query &= Q(block_height__lte=int(end))
    content_objects = content_objects.filter(content_query)

    if query:
        search_query = SearchQuery(query, config="english")
        content_objects = (
            content_objects.filter(search_vector=search_query)
            .annotate(rank=SearchRank(F("search_vector"), search_query))
            .order_by(
                "-rank",  # Sort by relevance first
                "block_time" if order == "asc" else "-block_time",  # Then by time
            )
        )
    else:
        # If no query, just order by time
        content_objects = content_objects.order_by(
            "block_time" if order == "asc" else "-block_time"
        )
    paginator = Paginator(content_objects, 12)
    page = request.GET.get("page")
    page_objects = paginator.get_page(page)

    for obj in page_objects:
        if obj.inscription:
            object_type = "Inscription"
            filename = obj.inscription.filename
            text = obj.inscription.text
            text_json = obj.inscription.json
            block = obj.inscription.txin.tx.block
            txid = obj.inscription.txin.tx.txid
        elif obj.op_return:
            object_type = "OpReturn"
            filename = None
            text = obj.op_return.scriptpubkey_text
            text_json = None
            block = obj.op_return.txout.tx.block
            txid = obj.op_return.txout.tx.txid
        elif obj.coinbase_scriptsig:
            object_type = "CoinbaseScriptsig"
            filename = None
            text = obj.coinbase_scriptsig.scriptsig_text
            text_json = None
            block = obj.coinbase_scriptsig.txin.tx.block
            txid = obj.coinbase_scriptsig.txin.tx.txid
        else:
            return HttpResponseBadRequest()
        url = f"/context/{obj.context_revision.id}"

        block_timestamp = datetime.fromtimestamp(block.time, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )

        results.append(
            {
                "object_type": object_type,
                "mime_type": obj.mime_type,
                "mime_subtype": obj.mime_subtype,
                "url": url,
                "filename": filename,
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


def block(request, block_identifier: str):
    offset = request.GET.get("offset", 0)
    limit = request.GET.get("limit", 1024)
    try:
        limit = int(limit)
    except ValueError:
        limit = 4096
    fmt = request.GET.get("fmt", "hex")
    if fmt not in ["hex", "json"]:
        # default to hex if format is not valid
        fmt = "hex"
    # determine file ext in s3 based on fmt
    if fmt == "hex":
        ext = ".bin"
    elif fmt == "json":
        ext = ".json"

    try:
        blockheight = int(block_identifier)
        block = get_object_or_404(models.Block, blockheight=blockheight)
    except ValueError:
        blockheaderhash = block_identifier
        block = get_object_or_404(models.Block, blockheaderhash=blockheaderhash)

    block_head_s3 = get_object_head_from_s3(f"block{block.blockheight}{ext}")
    if limit == -1:
        if fmt == "hex":
            content = (
                get_object_from_s3(f"block{block.blockheight}.bin", offset=offset)
                .read()
                .hex()
            )
        elif fmt == "json":
            content = (
                get_object_from_s3(f"block{block.blockheight}.json", offset=offset)
                .read()
                .decode("utf-8")
            )
        else:
            content = ""
    else:
        if fmt == "hex":
            print(offset)
            content = (
                get_object_from_s3(f"block{block.blockheight}.bin", offset=offset)
                .read(limit)
                .hex()
            )
        elif fmt == "json":
            content = (
                get_object_from_s3(f"block{block.blockheight}.json", offset=offset)
                .read(limit)
                .decode("utf-8")
            )
        else:
            content = ""

    if request.headers.get("Content-Type") == "application/json":
        return JsonResponse(
            {
                "readable_size": readable_size(block_head_s3.get("ContentLength")),
                "contentlength": block_head_s3.get("ContentLength"),
                "fmt": fmt,
                "offset": int(offset),
                "limit": int(limit),
                "blockheight": block.blockheight,
                "blockheaderhash": block.blockheaderhash,
                "content": content,
            }
        )
    return render(
        request,
        "block.html",
        context={
            "readable_size": readable_size(block_head_s3.get("ContentLength")),
            "contentlength": block_head_s3.get("ContentLength"),
            "fmt": fmt,
            "offset": int(offset),
            "limit": int(limit),
            "blockheight": block.blockheight,
            "blockheaderhash": block.blockheaderhash,
            "content": content,
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


def bit(request):
    new_xpub = derive_from_path("M/0/0", settings.WALLET_XPUB.encode("utf-8"))
    new_pubkey = deserialized_extended_key(new_xpub, return_dict=True)["key"]
    new_addr = to_bitcoin_address(
        bits.crypto.hash160(bytes.fromhex(new_pubkey))
    ).decode("utf-8")
    barray = io.BytesIO()
    qr = qrcode.make(f"bitcoin:{new_addr}")
    qr.save(barray, format="png")
    qb = base64.b64encode(barray.getvalue()).decode("utf-8")
    return JsonResponse(
        {"addr": new_addr, "qr_data_uri": f"data:image/png;base64,{qb}"}
    )


def lit(request):
    creds = Credentials.from_path(".gl-certs/creds-2")
    scheduler = Scheduler("testnet", creds)
    node = scheduler.node()
    timestamp = int(1000 * time.time())
    # pylint: disable=no-member
    invoice = node.invoice(
        amount_msat=clnpb.AmountOrAny(amount=clnpb.Amount(msat=10000)),
        description=f"Test invoice - {timestamp}",
        label=f"inv{timestamp}",
    )
    # pylint: enable=no-member
    barray = io.BytesIO()
    qr = qrcode.make(invoice.bolt11)
    qr.save(barray, format="png")
    qb = base64.b64encode(barray.getvalue()).decode("utf-8")
    return JsonResponse(
        {
            "bolt11": invoice.bolt11,
            "qr_data_uri": f"data:image/png;base64,{qb}",
        }
    )


def media(request, filename: str):
    filepath = Path(settings.MEDIA_ROOT) / filename
    return FileResponse(filepath.open("rb"))
