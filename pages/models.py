from bits import compact_size_uint
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.db import models


class Block(models.Model):
    blockheight = models.IntegerField()
    blockheaderhash = models.CharField(unique=True)
    version = models.IntegerField()
    prev_blockheaderhash = models.CharField()
    merkle_root = models.CharField()
    time = models.IntegerField()
    bits = models.CharField()
    nonce = models.BigIntegerField()

    coinbase_tx = models.BinaryField()
    number_of_txns = models.IntegerField()

    def serialized(self) -> bytes:
        """
        Return serialized block bytes, up to and including coinbase transaction
        """
        return (
            self.version.to_bytes(4, "little")
            + bytes.fromhex(self.prev_blockheaderhash)[::-1]
            + bytes.fromhex(self.merkle_root)[::-1]
            + self.time.to_bytes(4, "little")
            + bytes.fromhex(self.bits)[::-1]
            + self.nonce.to_bytes(8, "little")
            + compact_size_uint(self.number_of_txns)
            + self.coinbase_tx
        )

    def __str__(self):
        return f"<Block height={self.blockheight}>"


class Tx(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    n = models.IntegerField()

    txid = models.CharField()
    wtxid = models.CharField()

    version = models.IntegerField()
    locktime = models.BigIntegerField()

    def __str__(self):
        return f"<Tx n={self.n} block={self.block}>"


class ContextRevision(models.Model):
    html = models.TextField(max_length=1000000)
    prev_revision = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"<ContextRevision id={self.id}>"


class Content(models.Model):
    hash = models.BinaryField(unique=True)
    mime_type = models.CharField(db_index=True)
    size = models.IntegerField()

    params = models.JSONField()

    coinbase_scriptsig = models.ForeignKey(
        "CoinbaseScriptsig", on_delete=models.CASCADE, null=True
    )
    op_return = models.ForeignKey("OpReturn", on_delete=models.CASCADE, null=True)
    inscription = models.ForeignKey("Inscription", on_delete=models.CASCADE, null=True)
    text = models.TextField(default="", db_index=True)

    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    block_time = models.BigIntegerField(null=True, db_index=True)

    context_revision = models.ForeignKey(
        ContextRevision, on_delete=models.CASCADE, null=True
    )

    def save(self):
        if self.context_revision_id is None:
            self.context_revision = ContextRevision()
            self.context_revision.save()
        super().save()

    def __str__(self):
        # pylint: disable=no-member
        if self.inscription_id is not None:
            return f"<Content hash={self.hash.hex()} mime_type={self.mime_type} size={self.size} inscription={self.inscription}>"
        elif self.coinbase_scriptsig_id is not None:
            return f"<Content hash={self.hash.hex()} mime_type={self.mime_type} size={self.size} coinbase_scriptsig={self.coinbase_scriptsig}>"
        elif self.op_return_id is not None:
            return f"<Content hash={self.hash.hex()} mime_type={self.mime_type} size={self.size} op_return={self.op_return}>"
        return f"<Content hash={self.hash.hex()} mime_type={self.mime_type} size={self.size}>"
        # pylint: enable=no-member


class TxIn(models.Model):
    tx = models.ForeignKey(Tx, on_delete=models.CASCADE)
    n = models.IntegerField()

    # outpoint
    txid = models.CharField()
    vout = models.BigIntegerField()

    sequence = models.BigIntegerField()

    def __str__(self):
        return f"<TxIn n={self.n} tx={self.tx}>"


class CoinbaseScriptsig(models.Model):
    txin = models.ForeignKey(TxIn, on_delete=models.CASCADE)
    scriptsig = models.BinaryField()
    scriptsig_text = models.CharField(null=True)

    context_revision = models.ForeignKey(ContextRevision, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.context_revision_id is None:
            self.context_revision = ContextRevision()
            self.context_revision.content_type = "CoinbaseScriptsig"
            self.context_revision.block_time = self.txin.tx.block.time
            self.context_revision.save()
        super().save(*args, **kwargs)


class TxOut(models.Model):
    tx = models.ForeignKey(Tx, on_delete=models.CASCADE)
    n = models.IntegerField()

    value = models.BigIntegerField()

    def __str__(self):
        return f"<TxOut n={self.n} txid={self.tx.txid}>"


class OpReturn(models.Model):
    txout = models.ForeignKey(TxOut, on_delete=models.CASCADE)
    scriptpubkey = models.BinaryField()
    scriptpubkey_text = models.CharField()

    context_revision = models.ForeignKey(ContextRevision, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.context_revision_id is None:
            self.context_revision = ContextRevision()
            self.context_revision.content_type = "OpReturn"
            self.context_revision.block_time = self.txout.tx.block.time
            self.context_revision.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"<OpReturn txout={self.txout}>"


class Inscription(models.Model):
    number = models.IntegerField(null=True)
    inscription_id = models.CharField(unique=True)

    content_hash = models.BinaryField(null=True, db_index=True)
    content_type = models.CharField()
    content_size = models.IntegerField()

    # MIME
    mime_type = models.CharField(db_index=True)
    mime_subtype = models.CharField(db_index=True)
    mime_params = models.JSONField(default=dict)

    filename = models.CharField(null=True)
    text = models.TextField(null=True, max_length=1024)
    json = models.JSONField(null=True)

    delegate = models.CharField(
        null=True
    )  # delegates this inscription to another's inscription_id
    metadata = models.BinaryField(null=True)  # CBOR
    pointer = models.BigIntegerField(
        null=True
    )  # pointer index to inscribe on sat other than sat 0
    properties = models.BinaryField(null=True)  # CBOR
    provenance = models.CharField(null=True)  # references parent inscription_id

    txin = models.ForeignKey(TxIn, on_delete=models.CASCADE)

    context_revision = models.ForeignKey(ContextRevision, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.context_revision_id is None:
            self.context_revision = ContextRevision()
            self.context_revision.content_type = "Inscription"
            self.context_revision.block_time = self.txin.tx.block.time
            self.context_revision.save()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.number is not None:
            return f"<Inscription number={self.number} txin={self.txin}>"
        return f"<Inscription id={self.id} txin={self.txin}>"
